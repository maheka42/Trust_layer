"""Transparent rule-based risk scoring (0–100). Not ML."""

from __future__ import annotations

from datetime import datetime

AMOUNT_MAX = 35
NEW_DEVICE_MAX = 20
MERCHANT_MAX = 20
UNUSUAL_TIME_MAX = 15
LOCATION_MAX = 10


def _hour(timestamp: str) -> int:
    return datetime.fromisoformat(timestamp).hour


def _amount_points(amount: float, average_amount: float) -> tuple[int, str]:
    """Scale amount risk by how far the amount is from the user's average."""
    if average_amount <= 0:
        return 0, "Average amount is unavailable, so no amount anomaly points were added."
    ratio = amount / average_amount
    if ratio <= 1.0:
        return 0, f"Amount {amount:.2f} is at or below the user average {average_amount:.2f}."
    if ratio <= 2.0:
        points = round((ratio - 1.0) / 1.0 * 6)
        return points, (
            f"Amount {amount:.2f} is {ratio:.1f}x the user average {average_amount:.2f} "
            f"(1-2x band -> {points}/{AMOUNT_MAX})."
        )
    if ratio <= 5.0:
        points = round(6 + (ratio - 2.0) / 3.0 * 14)
        return points, (
            f"Amount {amount:.2f} is {ratio:.1f}x the user average {average_amount:.2f} "
            f"(2-5x band -> {points}/{AMOUNT_MAX})."
        )
    if ratio <= 10.0:
        points = round(20 + (ratio - 5.0) / 5.0 * 12)
        return points, (
            f"Amount {amount:.2f} is {ratio:.1f}x the user average {average_amount:.2f} "
            f"(5-10x band -> {points}/{AMOUNT_MAX})."
        )
    extra = min(3, round((ratio - 10.0) / 10.0 * 3))
    points = 32 + extra
    return points, (
        f"Amount {amount:.2f} is {ratio:.1f}x the user average {average_amount:.2f} "
        f"(>10x band -> {points}/{AMOUNT_MAX})."
    )


def _merchant_points(merchant_check: dict, history: dict, merchant_id: str) -> tuple[int, str]:
    risk_tier = (merchant_check.get("risk_tier") or "unknown").lower()
    name = merchant_check.get("name") or merchant_id
    familiar = merchant_id in set(history.get("prior_merchant_ids") or [])
    familiarity = "previously used by this user" if familiar else "not seen in this user's prior history"

    if risk_tier == "low":
        return 0, f"Merchant {name} is low risk and added 0 points."
    if risk_tier == "medium":
        points = 4 if familiar else 10
        return points, (
            f"Merchant {name} is medium risk and {familiarity} "
            f"(-> {points}/{MERCHANT_MAX})."
        )
    if risk_tier == "high":
        points = 8 if familiar else MERCHANT_MAX
        return points, (
            f"Merchant {name} is high risk and {familiarity} "
            f"(-> {points}/{MERCHANT_MAX})."
        )
    points = 6 if familiar else 12
    return points, (
        f"Merchant {name} has unknown risk tier and {familiarity} "
        f"(-> {points}/{MERCHANT_MAX})."
    )


def calculate_risk(transaction: dict, history: dict, device_check: dict, merchant_check: dict) -> dict:
    """
    Rule-based score from five transparent factors. Weights never exceed:
    amount 35, new device 20, merchant 20, unusual time 15, location 10.
    Signals are emitted only for points that were actually added.
    """
    signals: list[dict] = []
    score = 0

    amount = float(transaction["amount"])
    average_amount = float(history.get("average_amount") or 0)
    amount_weight, amount_desc = _amount_points(amount, average_amount)
    if amount_weight > 0:
        score += amount_weight
        signals.append({"name": "amount_anomaly", "description": amount_desc, "weight": amount_weight})

    device_status = device_check.get("status")
    if device_status in {"unknown", "new"}:
        score += NEW_DEVICE_MAX
        if device_status == "unknown":
            device_desc = (
                f"Device {transaction.get('device_id')} is unknown for user "
                f"{transaction.get('user_id')} (-> {NEW_DEVICE_MAX}/{NEW_DEVICE_MAX})."
            )
        else:
            device_desc = (
                f"Device {transaction.get('device_id')} is not the user's primary device "
                f"(-> {NEW_DEVICE_MAX}/{NEW_DEVICE_MAX})."
            )
        signals.append(
            {
                "name": "new_device",
                "description": device_desc,
                "weight": NEW_DEVICE_MAX,
            }
        )

    merchant_weight, merchant_desc = _merchant_points(
        merchant_check, history, transaction.get("merchant_id") or ""
    )
    if merchant_weight > 0:
        score += merchant_weight
        signals.append({"name": "merchant_risk", "description": merchant_desc, "weight": merchant_weight})

    hour = _hour(transaction["timestamp"])
    if 0 <= hour <= 5:
        score += UNUSUAL_TIME_MAX
        signals.append(
            {
                "name": "unusual_time",
                "description": (
                    f"Transaction hour {hour:02d}:00 falls in the 12 AM-5 AM window "
                    f"(-> {UNUSUAL_TIME_MAX}/{UNUSUAL_TIME_MAX})."
                ),
                "weight": UNUSUAL_TIME_MAX,
            }
        )

    home_city = history.get("home_city")
    txn_city = transaction.get("city")
    if home_city and txn_city and txn_city != home_city:
        score += LOCATION_MAX
        signals.append(
            {
                "name": "location_mismatch",
                "description": (
                    f"Transaction city {txn_city} differs from home city {home_city} "
                    f"(-> {LOCATION_MAX}/{LOCATION_MAX})."
                ),
                "weight": LOCATION_MAX,
            }
        )

    score = max(0, min(100, int(score)))
    return {"score": score, "signals": signals}


def decide(score: int) -> str:
    if score < 30:
        return "ALLOW"
    if score <= 70:
        return "REVIEW"
    return "BLOCK"


_DRIVER_LABELS = {
    "amount_anomaly": "amount anomaly",
    "new_device": "new device",
    "merchant_risk": "merchant risk",
    "unusual_time": "unusual time",
    "location_mismatch": "location mismatch",
}


def primary_driver(signals: list[dict]) -> str | None:
    """Highest-weight triggered signal, or None if nothing fired."""
    triggered = [item for item in signals if (item.get("weight") or 0) > 0]
    if not triggered:
        return None
    top = max(triggered, key=lambda item: int(item.get("weight") or 0))
    name = top.get("name") or ""
    return _DRIVER_LABELS.get(name, name.replace("_", " "))
