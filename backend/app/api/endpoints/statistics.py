from typing import Optional
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession
import io

from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin
from app.models.customer import Customer, CustomerStatus
from app.models.order import Order, OrderStatus, AfterSales
from app.models.user import User

router = APIRouter()


@router.get("/addition-rate")
async def get_addition_rate(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    salesperson_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """添加率统计: 已添加数 / 分配数 × 100%"""
    if not start_date:
        start_date = date.today().replace(day=1)
    if not end_date:
        end_date = date.today()

    # 权限过滤
    base_filter = and_(Customer.assign_date >= start_date, Customer.assign_date <= end_date)
    if current_user.role == "employee":
        base_filter = and_(base_filter, Customer.assigned_to == current_user.id)
    elif salesperson_id:
        base_filter = and_(base_filter, Customer.assigned_to == salesperson_id)

    # 统计分配数
    assigned_query = select(
        Customer.assigned_to,
        func.count(Customer.id).label("assigned_count"),
        func.count(case((Customer.status.in_([CustomerStatus.added, CustomerStatus.converted]), 1))).label("added_count"),
    ).where(base_filter).group_by(Customer.assigned_to)

    result = await db.execute(assigned_query)
    rows = result.all()

    # 获取用户信息
    user_ids = [r[0] for r in rows if r[0]]
    users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
    users_map = {u.id: u.real_name for u in users_result.scalars().all()}

    data = []
    for row in rows:
        assigned_to, assigned_count, added_count = row
        data.append({
            "salesperson_id": assigned_to,
            "salesperson_name": users_map.get(assigned_to, "未知"),
            "assigned_count": assigned_count,
            "added_count": added_count,
            "addition_rate": round(added_count / assigned_count * 100, 2) if assigned_count > 0 else 0,
        })

    # 按添加率排序
    data.sort(key=lambda x: x["addition_rate"], reverse=True)
    return {"start_date": start_date.isoformat(), "end_date": end_date.isoformat(), "data": data}


@router.get("/conversion")
async def get_conversion_stats(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    salesperson_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """转化率统计: 成交客户 / 新好友(已添加) × 100%"""
    if not start_date:
        start_date = date.today().replace(day=1)
    if not end_date:
        end_date = date.today()

    base_filter = and_(Customer.add_date >= start_date, Customer.add_date <= end_date)
    if current_user.role == "employee":
        base_filter = and_(base_filter, Customer.assigned_to == current_user.id)
    elif salesperson_id:
        base_filter = and_(base_filter, Customer.assigned_to == salesperson_id)

    # 已添加的 + 已转化的
    conversion_query = select(
        Customer.assigned_to,
        func.count(Customer.id).label("new_friends"),
        func.count(case((Customer.status == CustomerStatus.converted, 1))).label("converted_count"),
    ).where(base_filter).group_by(Customer.assigned_to)

    result = await db.execute(conversion_query)
    rows = result.all()

    user_ids = [r[0] for r in rows if r[0]]
    users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
    users_map = {u.id: u.real_name for u in users_result.scalars().all()}

    data = []
    for row in rows:
        assigned_to, new_friends, converted_count = row
        data.append({
            "salesperson_id": assigned_to,
            "salesperson_name": users_map.get(assigned_to, "未知"),
            "new_friends": new_friends,
            "converted_count": converted_count,
            "conversion_rate": round(converted_count / new_friends * 100, 2) if new_friends > 0 else 0,
        })

    data.sort(key=lambda x: x["conversion_rate"], reverse=True)
    return {"start_date": start_date.isoformat(), "end_date": end_date.isoformat(), "data": data}


@router.get("/performance")
async def get_performance(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    salesperson_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """业绩核算: 实际业绩 = 订单总额 - 退款 - 拒收"""
    if not start_date:
        start_date = date.today().replace(day=1)
    if not end_date:
        end_date = date.today()

    base_filter = and_(Order.order_date >= start_date, Order.order_date <= end_date)
    if current_user.role == "employee":
        base_filter = and_(base_filter, Order.salesperson_id == current_user.id)
    elif salesperson_id:
        base_filter = and_(base_filter, Order.salesperson_id == salesperson_id)

    # 订单总额
    performance_query = select(
        Order.salesperson_id,
        func.sum(Order.total_amount).label("total_orders"),
        func.sum(case((Order.status.in_([OrderStatus.returned, OrderStatus.rejected]), Order.total_amount), else_=0)).label("deductions"),
        func.count(Order.id).label("order_count"),
    ).where(base_filter).group_by(Order.salesperson_id)

    result = await db.execute(performance_query)
    rows = result.all()

    user_ids = [r[0] for r in rows if r[0]]
    users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
    users_map = {u.id: u for u in users_result.scalars().all()}

    data = []
    for row in rows:
        sp_id, total_orders, deductions, order_count = row
        user = users_map.get(sp_id)
        actual_performance = (total_orders or 0) - (deductions or 0)
        data.append({
            "salesperson_id": sp_id,
            "salesperson_name": user.real_name if user else "未知",
            "team": user.team if user else None,
            "total_orders": round(total_orders or 0, 2),
            "deductions": round(deductions or 0, 2),
            "actual_performance": round(actual_performance, 2),
            "order_count": order_count,
        })

    data.sort(key=lambda x: x["actual_performance"], reverse=True)
    return {"start_date": start_date.isoformat(), "end_date": end_date.isoformat(), "data": data}


@router.get("/finance")
async def get_finance_stats(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """财务统计: 营收/成本/毛利/净利"""
    if not start_date:
        start_date = date.today().replace(day=1)
    if not end_date:
        end_date = date.today()

    base_filter = and_(Order.order_date >= start_date, Order.order_date <= end_date)

    # 营收统计
    revenue_query = select(
        func.sum(Order.total_amount).label("total_revenue"),
        func.sum(Order.cost_amount).label("total_cost"),
        func.sum(case((Order.status.in_([OrderStatus.returned, OrderStatus.rejected]), Order.total_amount), else_=0)).label("refunds"),
        func.count(Order.id).label("total_orders"),
    ).where(base_filter)

    result = await db.execute(revenue_query)
    row = result.one()

    total_revenue = row.total_revenue or 0
    total_cost = row.total_cost or 0
    refunds = row.refunds or 0
    actual_revenue = total_revenue - refunds
    gross_profit = actual_revenue - total_cost
    # 提成计算
    commission_query = select(
        func.sum(
            (Order.total_amount - case((Order.status.in_([OrderStatus.returned, OrderStatus.rejected]), Order.total_amount), else_=0)) * User.commission_rate
        )
    ).select_from(Order).join(User, Order.salesperson_id == User.id).where(base_filter)

    comm_result = await db.execute(commission_query)
    total_commission = comm_result.scalar() or 0
    net_profit = gross_profit - total_commission

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_revenue": round(total_revenue, 2),
        "actual_revenue": round(actual_revenue, 2),
        "refunds": round(refunds, 2),
        "total_cost": round(total_cost, 2),
        "gross_profit": round(gross_profit, 2),
        "total_commission": round(total_commission, 2),
        "net_profit": round(net_profit, 2),
        "total_orders": row.total_orders,
    }


@router.get("/export")
async def export_statistics(
    type: str = Query(..., description="addition_rate|conversion|performance|finance"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """导出统计数据为Excel"""
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active

    if type == "finance":
        ws.title = "财务统计"
        ws.append(["指标", "金额"])
        # Re-use finance logic
        if not start_date:
            start_date = date.today().replace(day=1)
        if not end_date:
            end_date = date.today()
        base_filter = and_(Order.order_date >= start_date, Order.order_date <= end_date)
        result = await db.execute(
            select(
                func.sum(Order.total_amount).label("total_revenue"),
                func.sum(Order.cost_amount).label("total_cost"),
                func.sum(case((Order.status.in_([OrderStatus.returned, OrderStatus.rejected]), Order.total_amount), else_=0)).label("refunds"),
            ).where(base_filter)
        )
        row = result.one()
        total_revenue = row.total_revenue or 0
        refunds = row.refunds or 0
        total_cost = row.total_cost or 0
        actual_revenue = total_revenue - refunds
        gross_profit = actual_revenue - total_cost
        ws.append(["总营收", total_revenue])
        ws.append(["退款/拒收", refunds])
        ws.append(["实际营收", actual_revenue])
        ws.append(["总成本", total_cost])
        ws.append(["毛利润", gross_profit])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=report_{type}.xlsx"},
    )
