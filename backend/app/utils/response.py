"""Unified pagination, error handling, and response utilities."""
from typing import TypeVar, Generic, Optional, Any, Callable
from pydantic import BaseModel
from fastapi import HTTPException

T = TypeVar("T")


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20


class PaginatedResponse(BaseModel, Generic[T]):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: list[T]


class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = "ok"
    data: Optional[T] = None


def make_paginated_response(
    items: list,
    total: int,
    page: int,
    page_size: int,
    serializer: Optional[Callable] = None,
) -> dict:
    if serializer:
        items = [serializer(item) for item in items]
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
        "items": items,
    }


def serialize_user(user) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "real_name": user.real_name,
        "phone": user.phone,
        "email": user.email,
        "role": user.role.value if hasattr(user.role, 'value') else user.role,
        "team": user.team,
        "commission_rate": user.commission_rate,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def serialize_order(order) -> dict:
    return {
        "id": order.id,
        "order_no": order.order_no,
        "customer_name": order.customer_name,
        "customer_phone": order.customer_phone,
        "product_name": order.product_name,
        "quantity": order.quantity,
        "unit_price": order.unit_price,
        "total_amount": order.total_amount,
        "cost_amount": order.cost_amount,
        "discount_amount": order.discount_amount,
        "actual_amount": order.actual_amount,
        "payment_status": order.payment_status.value if hasattr(order.payment_status, 'value') else order.payment_status,
        "salesperson_id": order.salesperson_id,
        "source": order.source,
        "channel": order.channel,
        "status": order.status.value if hasattr(order.status, 'value') else order.status,
        "order_date": order.order_date.isoformat() if order.order_date else None,
        "remark": order.remark,
        "created_at": order.created_at.isoformat() if order.created_at else None,
    }


def serialize_customer(customer) -> dict:
    assignee_name = None
    if hasattr(customer, 'assignee') and customer.assignee:
        assignee_name = customer.assignee.real_name
    return {
        "id": customer.id,
        "name": customer.name,
        "phone": customer.phone,
        "wechat": customer.wechat,
        "source": customer.source,
        "channel": customer.channel,
        "source_product": customer.source_product,
        "assigned_to": customer.assigned_to,
        "assignee_name": assignee_name,
        "status": customer.status.value if hasattr(customer.status, 'value') else customer.status,
        "assign_date": customer.assign_date.isoformat() if customer.assign_date else None,
        "add_date": customer.add_date.isoformat() if customer.add_date else None,
        "convert_date": customer.convert_date.isoformat() if customer.convert_date else None,
        "remark": customer.remark,
        "created_at": customer.created_at.isoformat() if customer.created_at else None,
    }


def serialize_product(product) -> dict:
    return {
        "id": product.id,
        "name": product.name,
        "category": product.category,
        "price": product.price,
        "cost": product.cost,
        "specs": product.specs,
        "sku": product.sku,
        "stock": product.stock,
        "is_active": product.is_active,
        "created_at": product.created_at.isoformat() if product.created_at else None,
    }
