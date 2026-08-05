"""User management endpoints."""
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_admin, get_current_user, get_password_hash
from app.models.models import User, UserRole
from app.utils.response import serialize_user, make_paginated_response

router = APIRouter()


# ── Schemas ──
class UserCreate(BaseModel):
    username: str
    password: str
    real_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    role: str = "employee"
    team: Optional[str] = None
    commission_rate: float = 0.0

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        v = v.strip()
        if len(v) < 3:
            raise ValueError('用户名至少3位')
        return v

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('密码至少6位')
        return v

    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        valid = [r.value for r in UserRole]
        if v not in valid:
            raise ValueError(f'角色无效，可选: {valid}')
        return v


class UserUpdate(BaseModel):
    real_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    team: Optional[str] = None
    commission_rate: Optional[float] = None
    avatar_url: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if v is not None and len(v) < 6:
            raise ValueError('密码至少6位')
        return v


# ── Endpoints ──
@router.get("")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    role: Optional[str] = None,
    team: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """List users with filters."""
    filters = []
    if keyword:
        filters.append(
            (User.real_name.ilike(f"%{keyword}%")) | (User.username.ilike(f"%{keyword}%"))
        )
    if role:
        filters.append(User.role == role)
    if team:
        filters.append(User.team == team)
    if is_active is not None:
        filters.append(User.is_active == is_active)

    from sqlalchemy import and_ as sa_and
    base_where = sa_and(*filters) if filters else None

    count_q = select(func.count(User.id))
    data_q = select(User)
    if base_where is not None:
        count_q = count_q.where(base_where)
        data_q = data_q.where(base_where)

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        data_q.order_by(User.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    users = result.scalars().all()

    return make_paginated_response(users, total, page, page_size, serialize_user)


@router.post("")
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Create a new user."""
    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    user = User(
        username=data.username,
        password_hash=get_password_hash(data.password),
        real_name=data.real_name,
        phone=data.phone,
        email=data.email,
        role=data.role,
        team=data.team,
        commission_rate=data.commission_rate,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"id": user.id, "message": "创建成功"}


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Update user info."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    update_data = data.model_dump(exclude_unset=True)
    if 'password' in update_data and update_data['password']:
        if len(update_data['password']) < 6:
            raise HTTPException(status_code=400, detail="密码至少6位")
        update_data['password_hash'] = get_password_hash(update_data.pop('password'))
    else:
        update_data.pop('password', None)

    for key, value in update_data.items():
        setattr(user, key, value)
    await db.commit()
    return {"message": "更新成功"}


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """Hard-delete user (with safety guards).
    - Cannot delete yourself.
    - Cannot delete the last active admin.
    - Cannot delete users with orders (FK constraint) - suggest disabling instead.
    - Reassign/clear customers.assigned_to and after_sales.handler_id.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="不能删除自己")

    if user.role == UserRole.admin:
        admin_count = (
            await db.execute(
                select(func.count(User.id)).where(
                    User.role == UserRole.admin, User.is_active == True
                )
            )
        ).scalar() or 0
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="不能删除最后一个管理员")

    # Users with orders cannot be hard-deleted (FK orders.salesperson_id NOT NULL)
    from app.models.models import Order
    order_count = (
        await db.execute(
            select(func.count(Order.id)).where(Order.salesperson_id == user_id)
        )
    ).scalar() or 0
    if order_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"该员工有 {order_count} 条订单记录，不能删除；请使用「禁用」",
        )

    # Clear FK references before delete
    from app.models.models import Customer, AfterSales
    await db.execute(
        Customer.__table__.update().where(Customer.assigned_to == user_id).values(assigned_to=None)
    )
    await db.execute(
        AfterSales.__table__.update().where(AfterSales.handler_id == user_id).values(handler_id=None)
    )

    await db.delete(user)
    await db.commit()
    return {"message": "删除成功"}


@router.post("/{user_id}/enable")
async def enable_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Re-enable a disabled user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.is_active = True
    await db.commit()
    return {"message": "已启用"}


@router.get("/simple")
async def list_users_simple(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return simple user list (for dropdowns/selectors)."""
    query = select(User.id, User.real_name, User.team, User.role).where(User.is_active == True)
    result = await db.execute(query)
    users = [
        {"id": r[0], "real_name": r[1], "team": r[2], "role": r[3].value if hasattr(r[3], 'value') else r[3]}
        for r in result.all()
    ]
    return {"items": users}
