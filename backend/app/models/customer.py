from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SAEnum, Date
from app.core.database import Base
import enum


class CustomerStatus(str, enum.Enum):
    unassigned = "unassigned"  # 未分配
    assigned = "assigned"  # 已分配
    added = "added"  # 已添加(微信好友)
    converted = "converted"  # 已转化(成交)
    lost = "lost"  # 流失


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True, index=True)
    wechat = Column(String(100), nullable=True)
    source = Column(String(200), nullable=True)  # 进线日期.渠道.引流产品.所属业务员
    channel = Column(String(100), nullable=True)  # 渠道
    source_product = Column(String(200), nullable=True)  # 引流产品
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    status = Column(SAEnum(CustomerStatus), default=CustomerStatus.unassigned, nullable=False, index=True)
    assign_date = Column(Date, nullable=True)  # 分配日期
    add_date = Column(Date, nullable=True)  # 添加日期
    convert_date = Column(Date, nullable=True)  # 转化日期
    remark = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
