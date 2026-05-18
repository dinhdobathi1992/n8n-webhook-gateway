"""
Idempotent DB migration script.
Runs as an init container before the app starts.
Safe to re-run on every deployment.
"""
import sqlite3
import sys

DB_PATH = sys.argv[1] if len(sys.argv) > 1 else "/data/gateway.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Migration 1: Add workflow_url to webhook_routes (from v1805)
cur.execute("PRAGMA table_info(webhook_routes)")
columns = [row[1] for row in cur.fetchall()]
if "workflow_url" not in columns:
    cur.execute("ALTER TABLE webhook_routes ADD COLUMN workflow_url VARCHAR(2048)")
    print("Added workflow_url column to webhook_routes")

# Migration 2: Create channel_rules table
cur.execute("""
    CREATE TABLE IF NOT EXISTS channel_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        route_id INTEGER NOT NULL REFERENCES webhook_routes(id),
        channel_id VARCHAR(64) NOT NULL,
        destination_url VARCHAR(2048) NOT NULL,
        workflow_url VARCHAR(2048),
        description VARCHAR(500),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
cur.execute("""
    CREATE INDEX IF NOT EXISTS ix_channel_rules_route_channel
    ON channel_rules(route_id, channel_id)
""")

conn.commit()
print(f"Migrations complete for {DB_PATH}")
conn.close()
