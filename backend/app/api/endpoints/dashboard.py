from datetime import date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.customer import Customer, CustomerStatus
from app.models.order import Order, OrderStatus, Shipment
from app.models.user import User

router = APIRouter()


@router.get("")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """数据总览看板"""
    today = date.today()
    month_start = today.replace(day=1)

    # 今日新客户
    today_new_customers = (await db.execute(
        select(func.count(Customer.id)).where(
            func.date(Customer.created_at) == today
        )
    )).scalar() or 0

    # 今日已分配
    today_assigned = (await db.execute(
        select(func.count(Customer.id)).where(
            Customer.assign_date == today
        )
    )).scalar() or 0

    # 今日已添加
    today_added = (await db.execute(
        select(func.count(Customer.id)).where(
            Customer.add_date == today
        )
    )).scalar() or 0

    # 今日添加率
    today_addition_rate = round(today_added / today_assigned * 100, 2) if today_assigned > 0 else 0

    # 今日订单/营收
    today_orders_result = await db.execute(
        select(
            func.count(Order.id),
            func.coalesce(func.sum(Order.total_amount), 0),
        ).where(Order.order_date == today)
    )
    today_order_row = today_orders_result.one()
    today_order_count = today_order_row[0]
    today_revenue = round(today_order_row[1], 2)

    # 今日发货
    today_shipped = (await db.execute(
        select(func.count(Shipment.id)).where(Shipment.ship_date == today)
    )).scalar() or 0

    # 今日转化
    today_converted = (await db.execute(
        select(func.count(Customer.id)).where(Customer.convert_date == today)
    )).scalar() or 0

    # 本月业绩
    month_result = await db.execute(
        select(
            func.coalesce(func.sum(Order.total_amount), 0),
            func.coalesce(func.sum(case((Order.status.in_([OrderStatus.returned, OrderStatus.rejected]), Order.total_amount), else_=0)), 0),
            func.coalesce(func.sum(Order.cost_amount), 0),
            func.count(Order.id),
        ).where(and_(Order.order_date >= month_start, Order.order_date <= today))
    )
    month_row = month_result.one()
    month_total = round(month_row[0], 2)
    month_deductions = round(month_row[1], 2)
    month_cost = round(month_row[2], 2)
    month_actual = round(month_total - month_deductions, 2)
    month_profit = round(month_actual - month_cost, 2)
    month_order_count = month_row[3]

    # 团队排行（本月）
    team_ranking_result = await db.execute(
        select(
            User.real_name,
            User.team,
            func.coalesce(func.sum(Order.total_amount), 0).label("total"),
        ).select_from(Order).join(User, Order.salesperson_id == User.id).where(
            and_(Order.order_date >= month_start, Order.order_date <= today)
        ).group_by(User.id, User.real_name, User.team).order_by(func.sum(Order.total_amount).desc()).limit(10)
    )
    rankings = [
        {"name": r[0], "team": r[1], "total": round(r[2], 2)}
        for r in team_ranking_result.all()
    ]

    return {
        "today": {
            "new_customers": today_new_customers,
            "assigned": today_assigned,
            "added": today_added,
            "addition_rate": today_addition_rate,
            "orders": today_order_count,
            "revenue": today_revenue,
            "shipped": today_shipped,
            "converted": today_converted,
        },
        "month": {
            "total_revenue": month_total,
            "actual_revenue": month_actual,
            "deductions": month_deductions,
            "cost": month_cost,
            "profit": month_profit,
            "order_count": month_order_count,
        },
        "rankings": rankings,
    }
