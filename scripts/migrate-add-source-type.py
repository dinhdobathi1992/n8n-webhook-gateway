"""One-time migration: add source_type and secret_header_name columns."""
import asyncio

from app.db import engine


async def migrate():
    async with engine.begin() as conn:
        await conn.exec_driver_sql(
            "ALTER TABLE webhook_routes ADD COLUMN source_type VARCHAR(32) NOT NULL DEFAULT 'slack'"
        )
        await conn.exec_driver_sql(
            "ALTER TABLE webhook_routes ADD COLUMN secret_header_name VARCHAR(255)"
        )
        print("Migration complete: added source_type, secret_header_name")


asyncio.run(migrate())
