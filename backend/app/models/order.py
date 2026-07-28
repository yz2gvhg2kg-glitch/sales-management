from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SAEnum, Date, Text
from app.core.database import Base
import enum


class OrderStatus(str, enum.Enum):
    pending = "pending"  # 待发货
    shipped = "shipped"  # 已发货
    completed = "completed"  # 已完成
    returned = "returned"  # 已退货
    exchanged = "exchanged"  # 已换货
    rejected = "rejected"  # 已拒收


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    customer_name = Column(String(100), nullable=True)
    customer_phone = Column(String(20), nullable=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    product_name = Column(String(200), nullable=True)
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    cost_amount = Column(Float, default=0)  # 成本
    salesperson_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    source = Column(String(200), nullable=True)  # 进线来源
    status = Column(SAEnum(OrderStatus), default=OrderStatus.pending, nullable=False, index=True)
    order_date = Column(Date, nullable=False)
    remark = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    tracking_no = Column(String(100), nullable=True, index=True)
    carrier = Column(String(50), nullable=True)  # 快递公司
    ship_date = Column(Date, nullable=True)
    status = Column(String(50), default="shipped")  # shipped/delivered/returned
    created_at = Column(DateTime, default=datetime.utcnow)


class AfterSales(Base):
    __tablename__ = "after_sales"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    type = Column(String(20), nullable=False)  # return/exchange/rejection
    reason = Column(Text, nullable=True)
    refund_amount = Column(Float, default=0)
    status = Column(String(20), default="pending")  # pending/approved/completed
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
