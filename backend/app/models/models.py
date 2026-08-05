from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Boolean, Float, DateTime, ForeignKey,
    Enum as SAEnum, Date, Text, Index
)
from sqlalchemy.orm import relationship
from app.models.base import BaseModel, TimestampMixin
import enum


# ══════════════════════════════════════════════════════
# Enums
# ══════════════════════════════════════════════════════
class UserRole(str, enum.Enum):
    admin = "admin"
    manager = "manager"
    employee = "employee"


class CustomerStatus(str, enum.Enum):
    unassigned = "unassigned"
    assigned = "assigned"
    added = "added"
    converted = "converted"
    lost = "lost"


class OrderStatus(str, enum.Enum):
    pending = "pending"
    shipped = "shipped"
    completed = "completed"
    returned = "returned"
    exchanged = "exchanged"
    rejected = "rejected"


class PaymentStatus(str, enum.Enum):
    unpaid = "unpaid"
    partial = "partial"
    paid = "paid"
    refunded = "refunded"


class AfterSalesType(str, enum.Enum):
    return_refund = "return_refund"
    exchange = "exchange"
    rejection = "rejection"


class AfterSalesStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    completed = "completed"
    rejected = "rejected"


# ══════════════════════════════════════════════════════
# Models
# ══════════════════════════════════════════════════════
class User(BaseModel):
    __tablename__ = "users"
    __table_args__ = (
        Index("idx_users_role_active", "role", "is_active"),
        Index("idx_users_team", "team"),
    )

    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    real_name = Column(String(50), nullable=False)
    phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True, unique=True)  # NEW
    avatar_url = Column(String(500), nullable=True)  # NEW
    role = Column(SAEnum(UserRole), default=UserRole.employee, nullable=False)
    team = Column(String(50), nullable=True)
    commission_rate = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    last_login_at = Column(DateTime, nullable=True)  # NEW
    last_login_ip = Column(String(50), nullable=True)  # NEW

    # Relationships
    orders = relationship("Order", back_populates="salesperson", lazy="selectin")
    assigned_customers = relationship("Customer", back_populates="assignee", foreign_keys="Customer.assigned_to", lazy="selectin")


class Product(BaseModel):
    __tablename__ = "products"
    __table_args__ = (
        Index("idx_products_category_active", "category", "is_active"),
    )

    name = Column(String(200), nullable=False, index=True)
    category = Column(String(100), nullable=True)
    price = Column(Float, nullable=False)
    cost = Column(Float, nullable=False, default=0)
    specs = Column(Text, nullable=True)
    sku = Column(String(100), nullable=True, unique=True)
    image_url = Column(String(500), nullable=True)  # NEW
    stock = Column(Integer, default=0)  # NEW
    is_active = Column(Boolean, default=True)


class Customer(BaseModel):
    __tablename__ = "customers"
    __table_args__ = (
        Index("idx_customers_status_assigned", "status", "assigned_to"),
        Index("idx_customers_date_status", "assign_date", "status"),
    )

    name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True, index=True)
    wechat = Column(String(100), nullable=True)
    source = Column(String(200), nullable=True)
    channel = Column(String(100), nullable=True)
    source_product = Column(String(200), nullable=True)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    status = Column(SAEnum(CustomerStatus), default=CustomerStatus.unassigned, nullable=False, index=True)
    assign_date = Column(Date, nullable=True)
    add_date = Column(Date, nullable=True)
    convert_date = Column(Date, nullable=True)
    lost_date = Column(Date, nullable=True)  # NEW
    lost_reason = Column(String(500), nullable=True)  # NEW
    remark = Column(Text, nullable=True)

    # Relationship
    assignee = relationship("User", back_populates="assigned_customers", foreign_keys=[assigned_to], lazy="selectin")


class Order(BaseModel):
    __tablename__ = "orders"
    __table_args__ = (
        Index("idx_orders_date_status", "order_date", "status"),
        Index("idx_orders_salesperson_date", "salesperson_id", "order_date"),
        Index("idx_orders_customer", "customer_id"),
    )

    order_no = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    customer_name = Column(String(100), nullable=True)
    customer_phone = Column(String(20), nullable=True)
    address = Column(String(500), nullable=True)  # NEW: 收货地址
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    product_name = Column(String(200), nullable=True)
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    cost_amount = Column(Float, default=0)
    discount_amount = Column(Float, default=0)  # NEW: 优惠金额
    actual_amount = Column(Float, nullable=True)  # NEW: 实付金额
    payment_status = Column(SAEnum(PaymentStatus), default=PaymentStatus.unpaid)  # NEW
    salesperson_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    source = Column(String(200), nullable=True)
    channel = Column(String(100), nullable=True)  # NEW
    status = Column(SAEnum(OrderStatus), default=OrderStatus.pending, nullable=False, index=True)
    order_date = Column(Date, nullable=False)
    delivery_date = Column(Date, nullable=True)  # NEW
    remark = Column(Text, nullable=True)

    # Relationships
    salesperson = relationship("User", back_populates="orders", lazy="selectin")


class Shipment(BaseModel):
    __tablename__ = "shipments"
    __table_args__ = (
        Index("idx_shipments_order", "order_id"),
        Index("idx_shipments_tracking", "tracking_no"),
    )

    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    tracking_no = Column(String(100), nullable=True, index=True)
    carrier = Column(String(50), nullable=True)
    ship_date = Column(Date, nullable=True)
    delivery_date = Column(Date, nullable=True)  # NEW
    status = Column(String(50), default="shipped")  # shipped/delivered/returned
    shipping_fee = Column(Float, default=0)  # NEW
    remark = Column(Text, nullable=True)  # NEW


class AfterSales(BaseModel):
    __tablename__ = "after_sales"
    __table_args__ = (
        Index("idx_after_sales_order", "order_id"),
        Index("idx_after_sales_type_status", "type", "status"),
    )

    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    type = Column(SAEnum(AfterSalesType), nullable=False)
    reason = Column(Text, nullable=True)
    refund_amount = Column(Float, default=0)
    exchange_product = Column(String(200), nullable=True)  # NEW
    status = Column(SAEnum(AfterSalesStatus), default=AfterSalesStatus.pending)
    handler_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # NEW
    processed_at = Column(DateTime, nullable=True)
    remark = Column(Text, nullable=True)  # NEW
