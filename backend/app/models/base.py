"""Core abstract base model with common fields & methods."""
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, func
from app.core.database import Base


class TimestampMixin:
    """Adds created_at / updated_at with server defaults."""
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class BaseModel(Base, TimestampMixin):
    """Abstract base with auto-increment PK and timestamp mixin."""
    __abstract__ = True
    id = Column(Integer, primary_key=True, autoincrement=True)

    def to_dict(self, *fields: str) -> dict:
        """Convert model instance to dict with selected fields."""
        all_fields = {c.name for c in self.__table__.columns}
        selected = fields or all_fields
        return {f: getattr(self, f) for f in selected if f in all_fields}
