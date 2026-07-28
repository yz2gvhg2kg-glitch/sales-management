from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, Enum as SAEnum
from app.core.database import Base
import enum


class UserRole(str, enum.Enum):
    admin = "admin"
    manager = "manager"  # 主管
    employee = "employee"  # 业务员


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    real_name = Column(String(50), nullable=False)
    phone = Column(String(20), nullable=True)
    role = Column(SAEnum(UserRole), default=UserRole.employee, nullable=False)
    team = Column(String(50), nullable=True)  # 所属团队
    commission_rate = Column(Float, default=0.0)  # 提成比例
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
