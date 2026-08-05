"""Order endpoints with optimized queries and batch operations."""
from typing import Optional
from datetime import date, datetime
import io

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, field_validator
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin
from app.models.models import Order, OrderStatus, AfterSales, AfterSalesType, AfterSalesStatus, User, Shipment
from app.utils.helpers import generate_order_no, safe_int, safe_float, safe_str, parse_excel
from app.utils.response import serialize_order, make_paginated_response

router = APIRouter()


# ── Schemas ──
class OrderCreate(BaseModel):
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    product_name: str
    product_id: Optional[int] = None
    quantity: int = 1
    unit_price: float
    total_amount: float
    cost_amount: float = 0
    discount_amount: float = 0
    actual_amount: Optional[float] = None
    source: Optional[str] = None
    channel: Optional[str] = None
    order_date: date
    remark: Optional[str] = None

    @field_validator('customer_phone')
    @classmethod
    def clean_phone(cls, v):
        from app.utils.helpers import sanitize_phone
        return sanitize_phone(v)


class OrderStatusUpdate(BaseModel):
    status: str
    remark: Optional[str] = None


class AfterSalesCreate(BaseModel):
    order_id: int
    type: str  # return_refund / exchange / rejection
    reason: Optional[str] = None
    refund_amount: float = 0
    exchange_product: Optional[str] = None


# ── Endpoints ──
@router.get("")
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    salesperson_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    payment_status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List orders with filters, paginated. Single query for data+count."""
    # Build base filters
    filters = []
    count_filters = []

    # Role-based filtering
    if current_user.role == "employee":
        filters.append(Order.salesperson_id == current_user.id)
    elif salesperson_id:
        filters.append(Order.salesperson_id == salesperson_id)

    if status:
        filters.append(Order.status == status)
    if payment_status:
        filters.append(Order.payment_status == payment_status)
    if keyword:
        kw_filter = or_(
            Order.customer_name.ilike(f"%{keyword}%"),
            Order.order_no.ilike(f"%{keyword}%"),
            Order.product_name.ilike(f"%{keyword}%"),
            Order.customer_phone.ilike(f"%{keyword}%"),
        )
        filters.append(kw_filter)
    if start_date:
        filters.append(Order.order_date >= start_date)
    if end_date:
        filters.append(Order.order_date <= end_date)

    # Query: count + data in ONE round trip where possible
    base_where = and_(*filters) if filters else None
    if base_where is not None:
        count_q = select(func.count(Order.id)).where(base_where)
        data_q = select(Order).where(base_where)
    else:
        count_q = select(func.count(Order.id))
        data_q = select(Order)

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        data_q.order_by(Order.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    orders = result.scalars().all()

    # Attach tracking_no from shipments (one shipment per order, or latest)
    tracking_map = {}
    if orders:
        order_ids = [o.id for o in orders]
        ship_q = (
            select(Shipment.order_id, Shipment.tracking_no)
            .where(Shipment.order_id.in_(order_ids))
            .order_by(Shipment.id.desc())
        )
        ship_result = await db.execute(ship_q)
        for s_order_id, s_tracking in ship_result.all():
            if s_order_id not in tracking_map and s_tracking:
                tracking_map[s_order_id] = s_tracking

    items = [serialize_order(o, tracking_map.get(o.id)) for o in orders]
    return make_paginated_response(items, total, page, page_size)


@router.post("")
async def create_order(
    data: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a single order."""
    order_no = generate_order_no()
    order = Order(
        order_no=order_no,
        salesperson_id=current_user.id,
        **data.model_dump(),
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return {"id": order.id, "order_no": order_no, "message": "创建成功"}


@router.put("/{order_id}/status")
async def update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Update order status."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    valid_statuses = [s.value for s in OrderStatus]
    if data.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"无效状态，可选: {valid_statuses}")

    order.status = data.status
    if data.status == "delivered":
        order.delivery_date = date.today()
    await db.commit()
    return {"message": "状态已更新"}


@router.post("/import")
async def import_orders(
    file: UploadFile = File(...),
    salesperson_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Batch import orders from Excel. Admin imports for anyone; employees for self."""
    from app.utils.helpers import validate_file_upload
    validate_file_upload(file)

    content = await file.read()
    _, rows = parse_excel(content)

    if not rows:
        raise HTTPException(status_code=400, detail="文件中没有数据")

    # Determine salesperson
    sp_id = salesperson_id if current_user.role != "employee" and salesperson_id else current_user.id

    # Field mapping: Chinese OR English headers
    field_map = {
        "customer_name": ["客户姓名", "客户名称", "customer_name", "客户"],
        "customer_phone": ["电话", "手机", "phone", "customer_phone"],
        "product_name": ["产品", "产品名称", "product_name"],
        "quantity": ["数量", "quantity"],
        "unit_price": ["单价", "unit_price"],
        "total_amount": ["总金额", "金额", "total_amount"],
        "cost_amount": ["成本", "cost", "cost_amount"],
        "discount_amount": ["优惠", "优惠金额", "discount"],
        "source": ["来源", "渠道", "source", "channel"],
        "remark": ["备注", "remark"],
    }

    orders = []
    for row in rows:
        def get_field(field: str):
            for key in field_map.get(field, [field]):
                if key in row and row[key] is not None:
                    return row[key]
            return None

        order_no = generate_order_no()
        order = Order(
            order_no=order_no,
            customer_name=safe_str(get_field("customer_name")),
            customer_phone=safe_str(get_field("customer_phone")),
            product_name=safe_str(get_field("product_name"), "未知产品"),
            quantity=safe_int(get_field("quantity"), 1),
            unit_price=safe_float(get_field("unit_price")),
            total_amount=safe_float(get_field("total_amount")),
            cost_amount=safe_float(get_field("cost_amount")),
            discount_amount=safe_float(get_field("discount_amount")),
            source=safe_str(get_field("source")),
            remark=safe_str(get_field("remark")),
            salesperson_id=sp_id,
            order_date=date.today(),
        )
        orders.append(order)

    db.add_all(orders)
    await db.commit()
    return {"message": f"成功导入 {len(orders)} 条订单", "count": len(orders)}


@router.delete("/{order_id}")
async def delete_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Soft-delete (mark as rejected)."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    order.status = OrderStatus.rejected
    await db.commit()
    return {"message": "订单已作废"}


# ── After-Sales ──
@router.post("/after-sales")
async def create_after_sales(
    data: AfterSalesCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create after-sales record."""
    result = await db.execute(select(Order).where(Order.id == data.order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    # Permission: employees can only process their own orders
    if current_user.role == "employee" and order.salesperson_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作此订单")

    valid_types = [t.value for t in AfterSalesType]
    if data.type not in valid_types:
        raise HTTPException(status_code=400, detail=f"无效类型，可选: {valid_types}")

    after_sales = AfterSales(
        order_id=data.order_id,
        type=data.type,
        reason=data.reason,
        refund_amount=data.refund_amount,
        exchange_product=data.exchange_product,
        handler_id=current_user.id,
    )

    # Update order status
    status_map = {
        "return_refund": OrderStatus.returned,
        "exchange": OrderStatus.exchanged,
        "rejection": OrderStatus.rejected,
    }
    if data.type in status_map:
        order.status = status_map[data.type]

    db.add(after_sales)
    await db.commit()
    return {"message": "售后记录已创建", "id": after_sales.id}


@router.get("/after-sales")
async def list_after_sales(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """List after-sales records."""
    filters = []
    if status:
        filters.append(AfterSales.status == status)
    if type:
        filters.append(AfterSales.type == type)

    base_where = and_(*filters) if filters else None
    count_q = select(func.count(AfterSales.id)).where(base_where) if base_where is not None else select(func.count(AfterSales.id))
    data_q = select(AfterSales).where(base_where) if base_where is not None else select(AfterSales)

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        data_q.order_by(AfterSales.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    items = result.scalars().all()

    return make_paginated_response(items, total, page, page_size)
