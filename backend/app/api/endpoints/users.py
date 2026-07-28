from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_admin, get_password_hash
from app.models.user import User, UserRole

router = APIRouter()


class UserCreate(BaseModel):
    username: str
    password: str
    real_name: str
    phone: Optional[str] = None
    role: UserRole = UserRole.employee
    team: Optional[str] = None
    commission_rate: float = 0.0


class UserUpdate(BaseModel):
    real_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[UserRole] = None
    team: Optional[str] = None
    commission_rate: Optional[float] = None
    is_active: Optional[bool] = None


@router.get("")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    role: Optional[str] = None,
    team: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    query = select(User)
    count_query = select(func.count(User.id))

    if keyword:
        query = query.where(
            (User.real_name.contains(keyword)) | (User.username.contains(keyword))
        )
        count_query = count_query.where(
            (User.real_name.contains(keyword)) | (User.username.contains(keyword))
        )
    if role:
        query = query.where(User.role == role)
        count_query = count_query.where(User.role == role)
    if team:
        query = query.where(User.team == team)
        count_query = count_query.where(User.team == team)

    total = (await db.execute(count_query)).scalar()
    result = await db.execute(
        query.order_by(User.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    users = result.scalars().all()

    return {
        "total": total,
        "items": [
            {
                "id": u.id,
                "username": u.username,
                "real_name": u.real_name,
                "phone": u.phone,
                "role": u.role.value,
                "team": u.team,
                "commission_rate": u.commission_rate,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
    }


@router.post("")
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    existing = await db.execute(select(User).where(User.username == data.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    user = User(
        username=data.username,
        password_hash=get_password_hash(data.password),
        real_name=data.real_name,
        phone=data.phone,
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
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)
    await db.commit()
    return {"message": "更新成功"}


@router.delete("/{user_id}")
async def disable_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.is_active = False
    await db.commit()
    return {"message": "已禁用"}
