"""Unified statistics & dashboard endpoints — consolidated for code reuse."""
from typing import Optional
from datetime import date, datetime, timedelta
from collections import defaultdict

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, and_, case, or_
from sqlalchemy.ext.asyncio import AsyncSession
import io
import openpyxl

from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin
from app.models.models import (
    Customer, CustomerStatus, Order, OrderStatus, Shipment, AfterSales, User, Product,
)

router = APIRouter()


# ══════════════════════════════════════════════════════
# Helper: common user lookup
# ══════════════════════════════════════════════════════
async def _get_user_map(db: AsyncSession, user_ids: list[int]) -> dict:
    """Batch-fetch user info by IDs."""
    if not user_ids:
        return {}
    result = await db.execute(select(User).where(User.id.in_(user_ids)))
    return {u.id: u for u in result.scalars().all()}


async def _get_salesperson_filter(current_user: User, salesperson_id: Optional[int]):
    """Build role-aware salesperson filter."""
    if current_user.role == "employee":
        return current_user.id
    return salesperson_id


# ══════════════════════════════════════════════════════
# Dashboard (cached structure, single response)
# ══════════════════════════════════════════════════════
@router.get("/dashboard")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Comprehensive dashboard: today's stats + month summary + team rankings."""
    today = date.today()
    month_start = today.replace(day=1)
    sp_filter = None
    if current_user.role == "employee":
        sp_filter = current_user.id

    # ── Today's snapshot (single query per metric where possible) ──
    today_stats = {}

    # Customer stats in 3 queries (batched)
    cust_base = select(Customer)
    if sp_filter:
        cust_base = cust_base.where(Customer.assigned_to == sp_filter)

    today_stats["new_customers"] = (await db.execute(
        cust_base.where(func.date(Customer.created_at) == today).with_only_columns(func.count(Customer.id))
    )).scalar() or 0

    today_stats["assigned"] = (await db.execute(
        select(func.count(Customer.id))
        .where((Customer.assign_date == today) & ((Customer.assigned_to == sp_filter) if sp_filter else True))
    )).scalar() or 0

    today_stats["added"] = (await db.execute(
        select(func.count(Customer.id))
        .where((Customer.add_date == today) & ((Customer.assigned_to == sp_filter) if sp_filter else True))
    )).scalar() or 0

    today_stats["addition_rate"] = round(
        today_stats["added"] / today_stats["assigned"] * 100, 2
    ) if today_stats["assigned"] > 0 else 0

    # Order stats
    order_base = select(Customer)  # placeholder
    if sp_filter:
        order_base = Order.salesperson_id == sp_filter

    order_result = await db.execute(
        select(
            func.count(Order.id),
            func.coalesce(func.sum(Order.total_amount), 0),
        ).where(and_(Order.order_date == today, *(Order.salesperson_id == sp_filter,) if sp_filter else ()))
    )
    today_row = order_result.one()
    today_stats["orders"] = today_row[0]
    today_stats["revenue"] = round(today_row[1], 2)

    # Shipment
    today_stats["shipped"] = (await db.execute(
        select(func.count(Shipment.id)).where(Shipment.ship_date == today)
    )).scalar() or 0

    # Conversion
    today_stats["converted"] = (await db.execute(
        select(func.count(Customer.id))
        .where((Customer.convert_date == today) & ((Customer.assigned_to == sp_filter) if sp_filter else True))
    )).scalar() or 0

    # ── Month summary ──
    month_conds = [Order.order_date >= month_start, Order.order_date <= today]
    if sp_filter:
        month_conds.append(Order.salesperson_id == sp_filter)

    month_result = await db.execute(
        select(
            func.coalesce(func.sum(Order.total_amount), 0),
            func.coalesce(func.sum(case(
                (Order.status.in_([OrderStatus.returned, OrderStatus.rejected]), Order.total_amount),
                else_=0
            )), 0),
            func.coalesce(func.sum(Order.cost_amount), 0),
            func.count(Order.id),
        ).where(and_(*month_conds))
    )
    month_row = month_result.one()
    month_total = round(month_row[0], 2)
    month_deductions = round(month_row[1], 2)
    month_cost = round(month_row[2], 2)

    month = {
        "total_revenue": month_total,
        "actual_revenue": round(month_total - month_deductions, 2),
        "deductions": month_deductions,
        "cost": month_cost,
        "profit": round(month_total - month_deductions - month_cost, 2),
        "order_count": month_row[3],
    }

    # ── Team rankings ──
    ranking_result = await db.execute(
        select(
            User.real_name,
            User.team,
            func.coalesce(func.sum(Order.total_amount), 0).label("total"),
        )
        .select_from(Order)
        .join(User, Order.salesperson_id == User.id)
        .where(and_(*month_conds))
        .group_by(User.id, User.real_name, User.team)
        .order_by(func.sum(Order.total_amount).desc())
        .limit(10)
    )
    rankings = [{"name": r[0], "team": r[1], "total": round(r[2], 2)} for r in ranking_result.all()]

    return {
        "today": today_stats,
        "month": month,
        "rankings": rankings,
    }


# ══════════════════════════════════════════════════════
# Addition Rate
# ══════════════════════════════════════════════════════
@router.get("/addition-rate")
async def get_addition_rate(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    salesperson_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """添加率: added / assigned * 100% by salesperson."""
    if not start_date:
        start_date = date.today().replace(day=1)
    if not end_date:
        end_date = date.today()

    filters = [Customer.assign_date >= start_date, Customer.assign_date <= end_date]
    sp_id = await _get_salesperson_filter(current_user, salesperson_id)
    if sp_id:
        filters.append(Customer.assigned_to == sp_id)

    result = await db.execute(
        select(
            Customer.assigned_to,
            func.count(Customer.id).label("total"),
            func.count(case((Customer.status.in_([CustomerStatus.added, CustomerStatus.converted]), 1))).label("added"),
        ).where(and_(*filters)).group_by(Customer.assigned_to)
    )
    rows = result.all()
    user_map = await _get_user_map(db, [r[0] for r in rows if r[0]])

    data = [{
        "salesperson_id": r[0],
        "salesperson_name": user_map[r[0]].real_name if r[0] in user_map else "未知",
        "assigned_count": r[1],
        "added_count": r[2],
        "addition_rate": round(r[2] / r[1] * 100, 2) if r[1] > 0 else 0,
    } for r in rows]
    data.sort(key=lambda x: x["addition_rate"], reverse=True)
    return {"start_date": start_date.isoformat(), "end_date": end_date.isoformat(), "data": data}


# ══════════════════════════════════════════════════════
# Conversion Rate
# ══════════════════════════════════════════════════════
@router.get("/conversion")
async def get_conversion_stats(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    salesperson_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """转化率: converted / (added+converted) * 100% by salesperson."""
    if not start_date:
        start_date = date.today().replace(day=1)
    if not end_date:
        end_date = date.today()

    filters = [Customer.add_date >= start_date, Customer.add_date <= end_date]
    sp_id = await _get_salesperson_filter(current_user, salesperson_id)
    if sp_id:
        filters.append(Customer.assigned_to == sp_id)

    result = await db.execute(
        select(
            Customer.assigned_to,
            func.count(Customer.id).label("total"),
            func.count(case((Customer.status == CustomerStatus.converted, 1))).label("converted"),
        ).where(and_(*filters)).group_by(Customer.assigned_to)
    )
    rows = result.all()
    user_map = await _get_user_map(db, [r[0] for r in rows if r[0]])

    data = [{
        "salesperson_id": r[0],
        "salesperson_name": user_map[r[0]].real_name if r[0] in user_map else "未知",
        "new_friends": r[1],
        "converted_count": r[2],
        "conversion_rate": round(r[2] / r[1] * 100, 2) if r[1] > 0 else 0,
    } for r in rows]
    data.sort(key=lambda x: x["conversion_rate"], reverse=True)
    return {"start_date": start_date.isoformat(), "end_date": end_date.isoformat(), "data": data}


# ══════════════════════════════════════════════════════
# Performance
# ══════════════════════════════════════════════════════
@router.get("/performance")
async def get_performance(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    salesperson_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """业绩: actual = total - deductions (refund + rejection)."""
    if not start_date:
        start_date = date.today().replace(day=1)
    if not end_date:
        end_date = date.today()

    filters = [Order.order_date >= start_date, Order.order_date <= end_date]
    sp_id = await _get_salesperson_filter(current_user, salesperson_id)
    if sp_id:
        filters.append(Order.salesperson_id == sp_id)

    result = await db.execute(
        select(
            Order.salesperson_id,
            func.sum(Order.total_amount).label("total"),
            func.sum(case((Order.status.in_([OrderStatus.returned, OrderStatus.rejected]), Order.total_amount), else_=0)).label("deductions"),
            func.sum(Order.cost_amount).label("cost"),
            func.count(Order.id).label("count"),
        ).where(and_(*filters)).group_by(Order.salesperson_id)
    )
    rows = result.all()
    user_map = await _get_user_map(db, [r[0] for r in rows if r[0]])

    data = [{
        "salesperson_id": r[0],
        "salesperson_name": user_map[r[0]].real_name if r[0] in user_map else "未知",
        "team": user_map[r[0]].team if r[0] in user_map else None,
        "total_orders": round(r[1] or 0, 2),
        "deductions": round(r[2] or 0, 2),
        "cost_amount": round(r[3] or 0, 2),
        "actual_performance": round((r[1] or 0) - (r[2] or 0), 2),
        "gross_profit": round((r[1] or 0) - (r[2] or 0) - (r[3] or 0), 2),
        "order_count": r[4],
    } for r in rows]
    data.sort(key=lambda x: x["actual_performance"], reverse=True)
    return {"start_date": start_date.isoformat(), "end_date": end_date.isoformat(), "data": data}


# ══════════════════════════════════════════════════════
# Finance (admin only)
# ══════════════════════════════════════════════════════
@router.get("/finance")
async def get_finance_stats(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Finance overview: revenue, cost, profit, commissions."""
    if not start_date:
        start_date = date.today().replace(day=1)
    if not end_date:
        end_date = date.today()

    base_cond = and_(Order.order_date >= start_date, Order.order_date <= end_date)

    # Revenue + Cost
    revenue_result = await db.execute(
        select(
            func.coalesce(func.sum(Order.total_amount), 0),
            func.coalesce(func.sum(Order.cost_amount), 0),
            func.coalesce(func.sum(case(
                (Order.status.in_([OrderStatus.returned, OrderStatus.rejected]), Order.total_amount),
                else_=0
            )), 0),
            func.count(Order.id),
        ).where(base_cond)
    )
    row = revenue_result.one()
    total_revenue = round(row[0], 2)
    total_cost = round(row[1], 2)
    refunds = round(row[2], 2)

    # Commission calculation (join order x user)
    comm_result = await db.execute(
        select(
            func.coalesce(func.sum(
                (Order.total_amount - case(
                    (Order.status.in_([OrderStatus.returned, OrderStatus.rejected]), Order.total_amount),
                    else_=0
                )) * User.commission_rate
            ), 0)
        )
        .select_from(Order)
        .join(User, Order.salesperson_id == User.id)
        .where(base_cond)
    )
    total_commission = round(comm_result.scalar() or 0, 2)

    actual_revenue = round(total_revenue - refunds, 2)
    gross_profit = round(actual_revenue - total_cost, 2)
    net_profit = round(gross_profit - total_commission, 2)

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_revenue": total_revenue,
        "actual_revenue": actual_revenue,
        "refunds": refunds,
        "total_cost": total_cost,
        "gross_profit": gross_profit,
        "total_commission": total_commission,
        "net_profit": net_profit,
        "total_orders": row[3],
        "profit_margin": round(gross_profit / actual_revenue * 100, 2) if actual_revenue > 0 else 0,
    }


# ══════════════════════════════════════════════════════
# Trend (daily time-series for charts)
# ══════════════════════════════════════════════════════
@router.get("/trend")
async def get_trend(
    days: int = Query(30, ge=1, le=365),
    metric: str = Query("revenue", description="revenue / orders / customers / additions"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Daily trend data for line/bar charts."""
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    sp_filter = None if current_user.role != "employee" else current_user.id

    trend_data = []

    if metric == "revenue":
        base = select(
            Order.order_date,
            func.coalesce(func.sum(Order.total_amount), 0),
            func.count(Order.id),
        ).where(
            and_(Order.order_date >= start_date, Order.order_date <= end_date),
            *(Order.salesperson_id == sp_filter,) if sp_filter else (),
        ).group_by(Order.order_date).order_by(Order.order_date)

        result = await db.execute(base)
        for r in result.all():
            trend_data.append({"date": r[0].isoformat(), "revenue": round(r[1], 2), "orders": r[2]})

    elif metric == "customers":
        base = select(
            func.date(Customer.created_at),
            func.count(Customer.id),
        ).where(
            func.date(Customer.created_at) >= start_date,
            func.date(Customer.created_at) <= end_date,
            *(Customer.assigned_to == sp_filter,) if sp_filter else (),
        ).group_by(func.date(Customer.created_at)).order_by(func.date(Customer.created_at))

        result = await db.execute(base)
        for r in result.all():
            trend_data.append({"date": r[0].isoformat() if r[0] else None, "count": r[1]})

    elif metric == "additions":
        base = select(
            Customer.add_date,
            func.count(Customer.id),
        ).where(
            Customer.add_date >= start_date,
            Customer.add_date <= end_date,
            *(Customer.assigned_to == sp_filter,) if sp_filter else (),
        ).group_by(Customer.add_date).order_by(Customer.add_date)

        result = await db.execute(base)
        for r in result.all():
            trend_data.append({"date": r[0].isoformat() if r[0] else None, "count": r[1]})

    return {"start_date": start_date.isoformat(), "end_date": end_date.isoformat(), "data": trend_data}


# ══════════════════════════════════════════════════════
# Export (unified)
# ══════════════════════════════════════════════════════
@router.get("/export")
async def export_statistics(
    type: str = Query(..., description="addition_rate|conversion|performance|finance"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Export statistics as Excel."""
    if not start_date:
        start_date = date.today().replace(day=1)
    if not end_date:
        end_date = date.today()

    wb = openpyxl.Workbook()
    ws = wb.active

    if type == "finance":
        ws.title = "财务统计"
        base_cond = and_(Order.order_date >= start_date, Order.order_date <= end_date)
        result = await db.execute(
            select(
                func.coalesce(func.sum(Order.total_amount), 0),
                func.coalesce(func.sum(Order.cost_amount), 0),
                func.coalesce(func.sum(case(
                    (Order.status.in_([OrderStatus.returned, OrderStatus.rejected]), Order.total_amount),
                    else_=0
                )), 0),
            ).where(base_cond)
        )
        row = result.one()
        ws.append(["指标", "金额(元)"])
        ws.append(["总营收", row[0]])
        ws.append(["退款/拒收", row[2]])
        ws.append(["实际营收", row[0] - row[2]])
        ws.append(["总成本", row[1]])
        ws.append(["毛利润", row[0] - row[2] - row[1]])

    elif type == "addition_rate":
        ws.title = "添加率"
        ws.append(["业务员", "分配数", "已添加", "添加率(%)"])
        result = await db.execute(
            select(
                User.real_name,
                func.count(Customer.id).label("total"),
                func.count(case((Customer.status.in_([CustomerStatus.added, CustomerStatus.converted]), 1))).label("added"),
            )
            .select_from(Customer)
            .join(User, Customer.assigned_to == User.id)
            .where(and_(Customer.assign_date >= start_date, Customer.assign_date <= end_date))
            .group_by(User.id, User.real_name)
        )
        for r in result.all():
            ws.append([r[0], r[1], r[2], round(r[2] / r[1] * 100, 2) if r[1] > 0 else 0])

    elif type == "performance":
        ws.title = "业绩"
        ws.append(["业务员", "团队", "订单总额", "退款", "实际业绩", "订单数"])
        result = await db.execute(
            select(
                User.real_name,
                User.team,
                func.coalesce(func.sum(Order.total_amount), 0),
                func.coalesce(func.sum(case(
                    (Order.status.in_([OrderStatus.returned, OrderStatus.rejected]), Order.total_amount),
                    else_=0
                )), 0),
                func.count(Order.id),
            )
            .select_from(Order)
            .join(User, Order.salesperson_id == User.id)
            .where(and_(Order.order_date >= start_date, Order.order_date <= end_date))
            .group_by(User.id, User.real_name, User.team)
        )
        for r in result.all():
            ws.append([r[0], r[1], round(r[2], 2), round(r[3], 2), round(r[2] - r[3], 2), r[4]])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=report_{type}_{date.today()}.xlsx"},
    )
