"""User behavioral history and chargeback lookups."""

from __future__ import annotations

from collections import Counter
from datetime import datetime

from backend.database import get_connection


def _connect(conn):
    own = conn is None
    return (get_connection() if own else conn), own


def get_user_history(user_id: str, exclude_transaction_id: str | None = None, conn=None) -> dict:
    db, own = _connect(conn)
    try:
        user = db.execute(
            "SELECT id, city, country, typical_avg_amount FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if user is None:
            raise ValueError(f"Unknown user: {user_id}")

        params: list = [user_id]
        where = "user_id = ?"
        if exclude_transaction_id:
            where += " AND id != ?"
            params.append(exclude_transaction_id)

        rows = db.execute(
            f"""
            SELECT id, amount, timestamp, city, merchant_id
            FROM transactions
            WHERE {where}
            ORDER BY timestamp DESC
            """,
            params,
        ).fetchall()

        amounts = [float(row["amount"]) for row in rows]
        hours: list[int] = []
        merchant_ids: list[str] = []
        for row in rows:
            hours.append(datetime.fromisoformat(row["timestamp"]).hour)
            merchant_ids.append(row["merchant_id"])

        typical_hours = [hour for hour, _count in Counter(hours).most_common(3)]
        average_amount = (
            round(sum(amounts) / len(amounts), 2)
            if amounts
            else round(float(user["typical_avg_amount"]), 2)
        )
        recent = [
            {
                "id": row["id"],
                "amount": float(row["amount"]),
                "timestamp": row["timestamp"],
                "city": row["city"],
                "merchant_id": row["merchant_id"],
            }
            for row in rows[:5]
        ]
        return {
            "user_id": user_id,
            "average_amount": average_amount,
            "transaction_count": len(rows),
            "typical_hours": typical_hours,
            "home_city": user["city"],
            "home_country": user["country"],
            "recent_transactions": recent,
            "prior_merchant_ids": sorted(set(merchant_ids)),
        }
    finally:
        if own:
            db.close()


def check_previous_chargebacks(user_id: str, conn=None) -> dict:
    db, own = _connect(conn)
    try:
        rows = db.execute(
            """
            SELECT filed_at
            FROM chargebacks
            WHERE user_id = ?
            ORDER BY filed_at DESC
            """,
            (user_id,),
        ).fetchall()
        count = len(rows)
        latest = rows[0]["filed_at"] if rows else None
        return {
            "user_id": user_id,
            "chargeback_count": count,
            "most_recent_chargeback_date": latest,
            "has_historical_disputes": count > 0,
        }
    finally:
        if own:
            db.close()
