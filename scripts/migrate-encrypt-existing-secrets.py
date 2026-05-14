"""One-time migration: encrypt existing plaintext secrets in DB."""
import asyncio

from app.crypto import encrypt
from app.db import engine


async def migrate():
    async with engine.begin() as conn:
        rows = await conn.exec_driver_sql(
            "SELECT id, signing_secret, auth_header_value FROM webhook_routes"
        )
        count = 0
        for row in rows:
            rid, secret, auth_val = row
            new_secret = encrypt(secret) if secret else None
            new_auth = encrypt(auth_val) if auth_val else None
            if new_secret != secret or new_auth != auth_val:
                await conn.exec_driver_sql(
                    "UPDATE webhook_routes SET signing_secret = ?, auth_header_value = ? WHERE id = ?",
                    (new_secret, new_auth, rid),
                )
                count += 1
        print(f"Encrypted secrets for {count} route(s)")


asyncio.run(migrate())
