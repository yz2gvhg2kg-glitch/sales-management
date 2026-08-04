"""Shipment management endpoints."""
from typing import Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select, func, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_admin, get_current_user
from app.models.models import Order, OrderStatus, Shipment
from app.utils.helpers import safe_str, safe_int, parse_excel, validate_file_upload
from app.utils.response import make_paginated_response

router = APIRouter()


class ShipmentBatchCreate(BaseModel):
    order_ids: list[int]
    carrier: Optional[str] = None
    tracking_no: Optional[str] = None


class ShipmentTrackingUpdate(BaseModel):
    tracking_no: str
    carrier: Optional[str] = None
    shipping_fee: float = 0


# ── Endpoints ──
@router.get("")
async def list_shipments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    carrier: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """List shipment records."""
    filters = []
    if keyword:
        filters.append(Shipment.tracking_no.ilike(f"%{keyword}%"))
    if status:
        filters.append(Shipment.status == status)
    if carrier:
        filters.append(Shipment.carrier == carrier)

    base_where = and_(*filters) if filters else None
    count_q = select(func.count(Shipment.id)).where(base_where) if base_where is not None else select(func.count(Shipment.id))
    data_q = select(Shipment).where(base_where) if base_where is not None else select(Shipment)

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        data_q.order_by(Shipment.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    items = result.scalars().all()

    serialized = [{
        "id": s.id,
        "order_id": s.order_id,
        "tracking_no": s.tracking_no,
        "carrier": s.carrier,
        "ship_date": s.ship_date.isoformat() if s.ship_date else None,
        "delivery_date": s.delivery_date.isoformat() if s.delivery_date else None,
        "status": s.status,
        "shipping_fee": s.shipping_fee,
        "remark": s.remark,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    } for s in items]

    return make_paginated_response(serialized, total, page, page_size)


@router.post("/batch-ship")
async def batch_ship(
    data: ShipmentBatchCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Batch ship orders. Creates shipment records and updates order status."""
    today = date.today()

    # Verify orders exist and are in 'pending' status
    result = await db.execute(
        select(Order).where(
            Order.id.in_(data.order_ids),
            Order.status == OrderStatus.pending,
        )
    )
    pending_orders = result.scalars().all()
    if len(pending_orders) != len(data.order_ids):
        raise HTTPException(status_code=400, detail="部分订单不存在或状态不是待发货")

    shipments = [
        Shipment(
            order_id=oid,
            carrier=data.carrier,
            tracking_no=data.tracking_no,
            ship_date=today,
        )
        for oid in data.order_ids
    ]
    db.add_all(shipments)

    # Bulk update order status
    await db.execute(
        update(Order)
        .where(Order.id.in_(data.order_ids))
        .values(status=OrderStatus.shipped)
    )
    await db.commit()
    return {"message": f"成功发货 {len(data.order_ids)} 个订单"}


@router.put("/{shipment_id}/tracking")
async def update_tracking(
    shipment_id: int,
    data: ShipmentTrackingUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Update tracking number for a shipment."""
    result = await db.execute(select(Shipment).where(Shipment.id == shipment_id))
    shipment = result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail="发货记录不存在")

    shipment.tracking_no = data.tracking_no
    if data.carrier:
        shipment.carrier = data.carrier
    if data.shipping_fee > 0:
        shipment.shipping_fee = data.shipping_fee
    await db.commit()
    return {"message": "快递信息已更新"}


@router.post("/import-tracking")
async def import_tracking(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Batch import tracking numbers from Excel."""
    validate_file_upload(file)
    content = await file.read()
    _, rows = parse_excel(content)

    if not rows:
        raise HTTPException(status_code=400, detail="文件中没有数据")

    field_mappings = {
        "order_id": ["订单ID", "order_id", "订单编号"],
        "tracking_no": ["快递单号", "tracking_no", "运单号"],
        "carrier": ["快递公司", "carrier", "物流公司"],
    }

    updated = 0
    for row in rows:
        def get_val(field):
            for key in field_mappings.get(field, [field]):
                if key in row and row[key] is not None:
                    return row[key]
            return None

        order_id = safe_int(get_val("order_id"))
        tracking_no = safe_str(get_val("tracking_no"))
        carrier = safe_str(get_val("carrier"))

        if order_id and tracking_no:
            result = await db.execute(
                select(Shipment).where(Shipment.order_id == order_id)
            )
            shipment = result.scalar_one_or_none()
            if shipment:
                shipment.tracking_no = tracking_no
                if carrier:
                    shipment.carrier = carrier
                updated += 1

    await db.commit()
    return {"message": f"成功更新 {updated} 条快递信息", "updated": updated}


@router.put("/{shipment_id}/deliver")
async def mark_delivered(
    shipment_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Mark a shipment as delivered."""
    result = await db.execute(select(Shipment).where(Shipment.id == shipment_id))
    shipment = result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail="发货记录不存在")

    shipment.status = "delivered"
    shipment.delivery_date = date.today()

    # Also update order status
    await db.execute(
        update(Order).where(Order.id == shipment.order_id).values(status=OrderStatus.completed)
    )
    await db.commit()
    return {"message": "已标记为签收"}
