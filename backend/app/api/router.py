from fastapi import APIRouter

from app.api.endpoints import auth, users, products, customers, orders, shipments, statistics, dashboard

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(users.router, prefix="/users", tags=["员工管理"])
api_router.include_router(products.router, prefix="/products", tags=["产品管理"])
api_router.include_router(customers.router, prefix="/customers", tags=["客户管理"])
api_router.include_router(orders.router, prefix="/orders", tags=["订单管理"])
api_router.include_router(shipments.router, prefix="/shipments", tags=["发货管理"])
api_router.include_router(statistics.router, prefix="/statistics", tags=["数据统计"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["数据看板"])
