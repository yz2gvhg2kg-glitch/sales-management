from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, index=True)
    category = Column(String(100), nullable=True)  # 分类
    price = Column(Float, nullable=False)  # 售价
    cost = Column(Float, nullable=False, default=0)  # 成本
    specs = Column(Text, nullable=True)  # 规格/套餐描述
    sku = Column(String(100), nullable=True, unique=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
