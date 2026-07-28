from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_admin, get_current_user
from app.models.product import Product

router = APIRouter()


class ProductCreate(BaseModel):
    name: str
    category: Optional[str] = None
    price: float
    cost: float = 0
    specs: Optional[str] = None
    sku: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    cost: Optional[float] = None
    specs: Optional[str] = None
    sku: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("")
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    query = select(Product).where(Product.is_active == True)
    count_query = select(func.count(Product.id)).where(Product.is_active == True)

    if keyword:
        query = query.where(Product.name.contains(keyword))
        count_query = count_query.where(Product.name.contains(keyword))
    if category:
        query = query.where(Product.category == category)
        count_query = count_query.where(Product.category == category)

    total = (await db.execute(count_query)).scalar()
    result = await db.execute(
        query.order_by(Product.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    products = result.scalars().all()

    return {
        "total": total,
        "items": [
            {
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "price": p.price,
                "cost": p.cost,
                "specs": p.specs,
                "sku": p.sku,
                "is_active": p.is_active,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in products
        ],
    }


@router.post("")
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    product = Product(**data.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return {"id": product.id, "message": "创建成功"}


@router.put("/{product_id}")
async def update_product(
    product_id: int,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)
    await db.commit()
    return {"message": "更新成功"}


@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    product.is_active = False
    await db.commit()
    return {"message": "已删除"}
