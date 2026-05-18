"""One-time migration: encrypt or re-encrypt existing DB secrets."""
import os
import sqlite3
import sys

from cryptography.fernet import InvalidToken

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.crypto import decrypt, encrypt

DB_PATH = os.environ.get("DB_PATH", "gateway.db")


def normalize_secret(value: str | None) -> str | None:
    if not value:
        return value
    try:
        plaintext = decrypt(value)
    except InvalidToken:
        plaintext = value
    return encrypt(plaintext)


def migrate():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    rows = cur.execute("SELECT id, signing_secret, auth_header_value FROM webhook_routes").fetchall()

    updated = 0
    for row_id, signing_secret, auth_header_value in rows:
        new_ss = normalize_secret(signing_secret)
        new_ahv = normalize_secret(auth_header_value)

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
