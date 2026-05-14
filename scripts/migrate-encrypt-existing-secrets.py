"""One-time migration: encrypt existing plaintext secrets in DB."""
import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.crypto import encrypt

DB_PATH = os.environ.get("DB_PATH", "gateway.db")


def migrate():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    rows = cur.execute("SELECT id, signing_secret, auth_header_value FROM webhook_routes").fetchall()

    updated = 0
    for row_id, signing_secret, auth_header_value in rows:
        new_ss = encrypt(signing_secret) if signing_secret and not signing_secret.startswith("gAAAAA") else signing_secret
        new_ahv = encrypt(auth_header_value) if auth_header_value and not auth_header_value.startswith("gAAAAA") else auth_header_value

        if new_ss != signing_secret or new_ahv != auth_header_value:
            cur.execute(
                "UPDATE webhook_routes SET signing_secret = ?, auth_header_value = ? WHERE id = ?",
                (new_ss, new_ahv, row_id),
            )
            updated += 1

    conn.commit()
    conn.close()
    print(f"Encrypted {updated} rows")


if __name__ == "__main__":
    migrate()
