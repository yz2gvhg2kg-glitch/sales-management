"""Database initialization script — idempotent, creates tables + default admin."""
import asyncio
import time
import sys

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import select

from app.core.config import settings
from app.core.security import get_password_hash
from app.core.database import Base
from app.models.models import User


async def init_db():
    db_url = settings.async_database_url
    masked_url = db_url.split("@")[-1] if "@" in db_url else db_url[:30]
    print(f"→ Connecting to database at {masked_url}")

    for attempt in range(5):
        try:
            engine = create_async_engine(
                db_url,
                echo=False,
                pool_size=2,
                pool_pre_ping=True,
            )

            # Create all tables
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print("✓ Tables created/verified")

            # Create admin user if not exists
            from app.core.database import AsyncSessionLocal
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(User).where(User.username == "admin")
                )
                admin = result.scalar_one_or_none()

                if not admin:
                    admin_password = (
                        settings.SECRET_KEY[:8]
                        if settings.SECRET_KEY != "change-this-to-a-random-64-char-string"
                        else "admin123"
                    )
                    admin = User(
                        username="admin",
                        password_hash=get_password_hash(admin_password),
                        real_name="超级管理员",
                        phone="13800000000",
                        role="admin",
                        team="管理层",
                        commission_rate=0.0,
                        is_active=True,
                    )
                    session.add(admin)
                    await session.commit()
                    print(f"✓ Default admin user created (admin / {admin_password})")
                else:
                    print("✓ Admin user already exists")

            await engine.dispose()
            print("✓ Database initialization complete")
            return True

        except Exception as e:
            print(f"✗ DB init attempt {attempt + 1}/5 failed: {e}")
            if attempt < 4:
                delay = 2 ** attempt
                print(f"  Retrying in {delay}s...")
                time.sleep(delay)
            else:
                print("✗ All DB init attempts failed. Starting app anyway.")
                return False


if __name__ == "__main__":
    asyncio.run(init_db())
