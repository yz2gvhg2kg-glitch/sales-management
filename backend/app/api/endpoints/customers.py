"""Customer endpoints with batch import & operations."""
from typing import Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select, func, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin
from app.models.models import Customer, CustomerStatus, User
from app.utils.helpers import safe_str, safe_int, safe_float, parse_excel, validate_file_upload
from app.utils.response import serialize_customer, make_paginated_response

router = APIRouter()


# ── Schemas ──
class CustomerCreate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    wechat: Optional[str] = None
    source: Optional[str] = None
    channel: Optional[str] = None
    source_product: Optional[str] = None
    remark: Optional[str] = None


class CustomerBatchAssign(BaseModel):
    customer_ids: list[int]
    assigned_to: int


class CustomerStatusUpdate(BaseModel):
    status: str
    remark: Optional[str] = None


class CustomerBatchImport(BaseModel):
    """Metadata for batch import."""
    pass


# ── Endpoints ──
@router.get("")
async def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    assigned_to: Optional[int] = None,
    channel: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List customers with role-automated filtering."""
    filters = []

    # Role-based filtering
    if current_user.role == "employee":
        filters.append(Customer.assigned_to == current_user.id)
    elif assigned_to:
        filters.append(Customer.assigned_to == assigned_to)

    if status:
        filters.append(Customer.status == status)
    if channel:
        filters.append(Customer.channel == channel)
    if keyword:
        filters.append(or_(
            Customer.name.ilike(f"%{keyword}%"),
            Customer.phone.ilike(f"%{keyword}%"),
            Customer.wechat.ilike(f"%{keyword}%"),
        ))
    if start_date:
        filters.append(func.date(Customer.created_at) >= start_date)
    if end_date:
        filters.append(func.date(Customer.created_at) <= end_date)

    base_where = and_(*filters) if filters else None
    count_q = select(func.count(Customer.id)).where(base_where) if base_where is not None else select(func.count(Customer.id))
    data_q = select(Customer).where(base_where) if base_where is not None else select(Customer)

    total = (await db.execute(count_q)).scalar() or 0
    # Eager load assignee to avoid N+1
    result = await db.execute(
        data_q.order_by(Customer.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    customers = result.scalars().all()

    return make_paginated_response(customers, total, page, page_size, serialize_customer)


@router.post("")
async def create_customer(
    data: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Create a single customer."""
    customer = Customer(**data.model_dump())
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return {"id": customer.id, "message": "创建成功"}


@router.post("/import")
async def import_customers(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Batch import customers from Excel."""
    validate_file_upload(file)
    content = await file.read()
    _, rows = parse_excel(content)

    if not rows:
        raise HTTPException(status_code=400, detail="文件中没有数据")

    field_mappings = {
        "name": ["姓名", "客户名称", "name"],
        "phone": ["电话", "手机", "phone"],
        "wechat": ["微信", "wechat"],
        "channel": ["渠道", "channel"],
        "source": ["来源", "source"],
        "source_product": ["引流产品", "产品", "source_product"],
        "remark": ["备注", "remark"],
    }

    customers = []
    for row in rows:
        def get_val(field):
            for key in field_mappings.get(field, [field]):
                if key in row and row[key] is not None:
                    return row[key]
            return None

        customers.append(Customer(
            name=safe_str(get_val("name")),
            phone=safe_str(get_val("phone")),
            wechat=safe_str(get_val("wechat")),
            channel=safe_str(get_val("channel")),
            source=safe_str(get_val("source")),
            source_product=safe_str(get_val("source_product")),
            remark=safe_str(get_val("remark")),
        ))

    db.add_all(customers)
    await db.commit()
    return {"message": f"成功导入 {len(customers)} 条客户数据", "count": len(customers)}


@router.post("/assign")
async def assign_customers_batch(
    data: CustomerBatchAssign,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Batch assign customers to a salesperson."""
    today = date.today()

    # Verify assignee exists
    result = await db.execute(select(User).where(User.id == data.assigned_to, User.is_active == True))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="指定业务员不存在或已禁用")

    # Bulk update for performance
    await db.execute(
        update(Customer)
        .where(Customer.id.in_(data.customer_ids))
        .values(assigned_to=data.assigned_to, status=CustomerStatus.assigned, assign_date=today)
    )
    await db.commit()
    return {"message": f"成功分配 {len(data.customer_ids)} 个客户"}


@router.put("/{customer_id}/status")
async def update_customer_status(
    customer_id: int,
    data: CustomerStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update customer status (add/lost/converted)."""
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")

    # Permission check
    if current_user.role == "employee" and customer.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作此客户")

    valid_statuses = [s.value for s in CustomerStatus]
    if data.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"无效状态，可选: {valid_statuses}")

    today = date.today()
    customer.status = data.status
    if data.status == "added":
        customer.add_date = today
    elif data.status == "converted":
        customer.convert_date = today
    elif data.status == "lost":
        customer.lost_date = today
    if data.remark:
        customer.remark = data.remark

    await db.commit()
    return {"message": "状态已更新"}


@router.put("/{customer_id}")
async def update_customer(
    customer_id: int,
    data: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Update customer info."""
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")

    for key, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(customer, key, value)
    await db.commit()
    return {"message": "更新成功"}


@router.get("/stats/summary")
async def get_customer_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Customer statistics summary: count by status."""
    sp_filter = [Customer.assigned_to == current_user.id] if current_user.role == "employee" else []

    result = await db.execute(
        select(
            Customer.status,
            func.count(Customer.id),
        ).where(and_(*sp_filter)).group_by(Customer.status)
    )
    stats = {}
    for status, count in result.all():
        stats[status.value] = count

    return {
        "total": sum(stats.values()),
        "by_status": stats,
    }
