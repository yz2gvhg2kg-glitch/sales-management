"""Database initialization script - creates tables and default admin user."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.user import User, Base
from app.models.product import Product
from app.models.customer import Customer
from app.models.order import Order, Shipment, AfterSales


async def init_db():
    engine = create_async_engine(settings.DATABASE_URL, echo=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Check if admin exists
        result = await session.execute(select(User).where(User.username == "admin"))
        admin = result.scalar_one_or_none()

        if not admin:
            admin = User(
                username="admin",
                password_hash=get_password_hash("admin123"),
                real_name="超级管理员",
                phone="13800000000",
                role="admin",
                team="管理层",
                commission_rate=0.0,
                is_active=True,
            )
            session.add(admin)
            await session.commit()
            print("✓ Default admin user created (admin / admin123)")
        else:
            print("✓ Admin user already exists")

    await engine.dispose()
    print("✓ Database initialized successfully")


if __name__ == "__main__":
    asyncio.run(init_db())
