"""Device ownership and merchant profile lookups."""

from __future__ import annotations

from backend.database import get_connection


def _connect(conn):
    own = conn is None
    return (get_connection() if own else conn), own


def check_device(user_id: str, device_id: str, conn=None) -> dict:
    db, own = _connect(conn)
    try:
        row = db.execute(
            """
            SELECT id, user_id, device_type, first_seen, is_primary
            FROM devices
            WHERE id = ?
            """,
            (device_id,),
        ).fetchone()
        if row is None or row["user_id"] != user_id:
            return {
                "user_id": user_id,
                "device_id": device_id,
                "status": "unknown",
                "first_seen": None,
                "device_type": None,
                "is_primary": None,
            }
        # Established profile = primary device. Non-primary is treated as new
        # (fraud seed rows use a secondary device; traps/normal use primary).
        status = "known" if int(row["is_primary"]) == 1 else "new"
        return {
            "user_id": user_id,
            "device_id": device_id,
            "status": status,
            "first_seen": row["first_seen"],
            "device_type": row["device_type"],
            "is_primary": int(row["is_primary"]),
        }
    finally:
        if own:
            db.close()


def check_merchant(merchant_id: str, conn=None) -> dict:
    db, own = _connect(conn)
    try:
        row = db.execute(
            """
            SELECT id, name, category, risk_level
            FROM merchants
            WHERE id = ?
            """,
            (merchant_id,),
        ).fetchone()
        if row is None:
            return {
                "merchant_id": merchant_id,
                "name": None,
                "category": None,
                "risk_tier": "unknown",
            }
        return {
            "merchant_id": merchant_id,
            "name": row["name"],
            "category": row["category"],
            "risk_tier": row["risk_level"],
        }
    finally:
        if own:
            db.close()
