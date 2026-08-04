"""Product endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_admin, get_current_user
from app.models.models import Product
from app.utils.response import serialize_product, make_paginated_response

router = APIRouter()


class ProductCreate(BaseModel):
    name: str
    category: Optional[str] = None
    price: float
    cost: float = 0
    specs: Optional[str] = None
    sku: Optional[str] = None
    stock: int = 0
    image_url: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    cost: Optional[float] = None
    specs: Optional[str] = None
    sku: Optional[str] = None
    stock: Optional[int] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("")
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    category: Optional[str] = None,
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """List products."""
    filters = []
    if not include_inactive:
        filters.append(Product.is_active == True)
    if keyword:
        filters.append(Product.name.ilike(f"%{keyword}%"))
    if category:
        filters.append(Product.category == category)

    from sqlalchemy import and_ as sa_and
    base_where = sa_and(*filters) if filters else None

    count_q = select(func.count(Product.id)).where(base_where) if base_where is not None else select(func.count(Product.id))
    data_q = select(Product).where(base_where) if base_where is not None else select(Product)

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        data_q.order_by(Product.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    products = result.scalars().all()
    return make_paginated_response(products, total, page, page_size, serialize_product)


@router.post("")
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Create a product."""
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
    """Update a product."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(product, key, value)
    await db.commit()
    return {"message": "更新成功"}


@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Soft-delete a product."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    product.is_active = False
    await db.commit()
    return {"message": "已删除"}


@router.get("/categories")
async def get_categories(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """List distinct product categories."""
    result = await db.execute(
        select(Product.category).where(Product.is_active == True, Product.category.isnot(None)).distinct()
    )
    return {"categories": [r[0] for r in result.all()]}
