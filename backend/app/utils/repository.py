"""Generic repository with common CRUD + filtering + pagination."""
from typing import Optional, Type, TypeVar, Any
from sqlalchemy import select, func, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

T = TypeVar("T")


class BaseRepository:
    """Generic async repository for CRUD operations."""

    model: Type[Any]  # set in subclass

    def __init__(self, session: AsyncSession):
        self.session = session

    def _apply_pagination(self, query: Select, page: int, page_size: int) -> Select:
        return query.offset((page - 1) * page_size).limit(page_size) if page_size else query

    def _apply_ordering(self, query: Select, order_by: Any, desc: bool = True) -> Select:
        col = order_by if not desc else order_by.desc()
        return query.order_by(col)

    async def get_by_id(self, id: int) -> Optional[Any]:
        result = await self.session.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_all(self, **filters) -> list:
        query = select(self.model)
        for k, v in filters.items():
            if v is not None:
                query = query.where(getattr(self.model, k) == v)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, **kwargs) -> Any:
        instance = self.model(**kwargs)
        self.session.add(instance)
        return instance

    async def bulk_create(self, items: list[dict]) -> list:
        instances = [self.model(**item) for item in items]
        self.session.add_all(instances)
        return instances

    async def update(self, id: int, **kwargs) -> Optional[Any]:
        instance = await self.get_by_id(id)
        if instance:
            for k, v in kwargs.items():
                if hasattr(instance, k) and v is not None:
                    setattr(instance, k, v)
        return instance

    async def soft_delete(self, id: int) -> bool:
        instance = await self.get_by_id(id)
        if instance and hasattr(instance, "is_active"):
            instance.is_active = False
            return True
        return False

    async def count(self, **filters) -> int:
        query = select(func.count(self.model.id))
        for k, v in filters.items():
            if v is not None:
                query = query.where(getattr(self.model, k) == v)
        result = await self.session.execute(query)
        return result.scalar() or 0
