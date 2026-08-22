"""SQLite connection and schema for TrustLayer seed data."""

from __future__ import annotations

import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "seed_data.db"

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT NOT NULL UNIQUE,
    country TEXT NOT NULL,
    city TEXT NOT NULL,
    home_lat REAL NOT NULL,
    home_lng REAL NOT NULL,
    currency TEXT NOT NULL,
    typical_avg_amount REAL NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS devices (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    fingerprint TEXT NOT NULL UNIQUE,
    device_type TEXT NOT NULL,
    os_name TEXT NOT NULL,
    browser TEXT NOT NULL,
    is_primary INTEGER NOT NULL CHECK (is_primary IN (0, 1)),
    first_seen TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS merchants (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    country TEXT NOT NULL,
    mcc TEXT NOT NULL,
    risk_level TEXT NOT NULL CHECK (risk_level IN ('low', 'medium', 'high'))
);

CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    merchant_id TEXT NOT NULL,
    amount REAL NOT NULL,
    currency TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    city TEXT NOT NULL,
    country TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    channel TEXT NOT NULL,
    payment_method TEXT NOT NULL,
    card_last4 TEXT NOT NULL,
    ground_truth TEXT NOT NULL CHECK (ground_truth IN ('normal', 'fraud', 'trap')),
    UNIQUE (user_id, timestamp, amount, merchant_id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (device_id) REFERENCES devices(id),
    FOREIGN KEY (merchant_id) REFERENCES merchants(id)
);

CREATE TABLE IF NOT EXISTS chargebacks (
    id TEXT PRIMARY KEY,
    transaction_id TEXT NOT NULL UNIQUE,
    user_id TEXT NOT NULL,
    amount REAL NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL,
    filed_at TEXT NOT NULL,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_devices_user ON devices(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_ground_truth ON transactions(ground_truth);
CREATE INDEX IF NOT EXISTS idx_chargebacks_user ON chargebacks(user_id);
"""


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path is not None else DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def reset_db(conn: sqlite3.Connection) -> None:
    """Drop and recreate tables so re-runs never insert duplicates."""
    conn.executescript(
        """
        PRAGMA foreign_keys = OFF;
        DROP TABLE IF EXISTS chargebacks;
        DROP TABLE IF EXISTS transactions;
        DROP TABLE IF EXISTS devices;
        DROP TABLE IF EXISTS merchants;
        DROP TABLE IF EXISTS users;
        PRAGMA foreign_keys = ON;
        """
    )
    init_db(conn)


def fetch_counts(conn: sqlite3.Connection) -> dict[str, int]:
    def count(sql: str) -> int:
        return int(conn.execute(sql).fetchone()[0])

    return {
        "users": count("SELECT COUNT(*) FROM users"),
        "devices": count("SELECT COUNT(*) FROM devices"),
        "merchants": count("SELECT COUNT(*) FROM merchants"),
        "transactions": count("SELECT COUNT(*) FROM transactions"),
        "normal": count("SELECT COUNT(*) FROM transactions WHERE ground_truth = 'normal'"),
        "fraud": count("SELECT COUNT(*) FROM transactions WHERE ground_truth = 'fraud'"),
        "traps": count("SELECT COUNT(*) FROM transactions WHERE ground_truth = 'trap'"),
        "chargebacks": count("SELECT COUNT(*) FROM chargebacks"),
    }
