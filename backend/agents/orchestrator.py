"""Run the TrustLayer investigation pipeline with progress events."""

from __future__ import annotations

from collections.abc import Iterator

from backend.agents.device_agent import check_device, check_merchant
from backend.agents.explanation_agent import explain_risk
from backend.agents.history_agent import check_previous_chargebacks, get_user_history
from backend.agents.risk_engine import calculate_risk, decide, primary_driver
from backend.database import get_connection


def load_transaction(transaction_id: str, conn=None) -> dict:
    own = conn is None
    db = get_connection() if own else conn
    try:
        row = db.execute(
            """
            SELECT
                t.id, t.user_id, t.device_id, t.merchant_id, t.amount, t.currency,
                t.timestamp, t.ip_address, t.city, t.country, t.latitude, t.longitude,
                t.channel, t.payment_method, t.card_last4, t.ground_truth,
                m.name AS merchant
            FROM transactions t
            JOIN merchants m ON m.id = t.merchant_id
            WHERE t.id = ?
            """,
            (transaction_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"Unknown transaction: {transaction_id}")
        return dict(row)
    finally:
        if own:
            db.close()


def _event(message: str, **payload) -> dict:
    event = {"message": message}
    event.update(payload)
    return event


def score_transaction(transaction: dict, conn=None) -> dict:
    """Run agents + risk + decision without explanation (used by /stats)."""
    own = conn is None
    db = get_connection() if own else conn
    try:
        history = get_user_history(transaction["user_id"], transaction["id"], conn=db)
        device = check_device(transaction["user_id"], transaction["device_id"], conn=db)
        merchant = check_merchant(transaction["merchant_id"], conn=db)
        risk = calculate_risk(transaction, history, device, merchant)
        decision = decide(risk["score"])
        return {
            "score": risk["score"],
            "signals": risk["signals"],
            "decision": decision,
            "primary_driver": primary_driver(risk["signals"]),
            "history": history,
            "device_check": device,
            "merchant_check": merchant,
        }
    finally:
        if own:
            db.close()


def investigate(transaction_id: str, include_explanation: bool = True) -> Iterator[dict]:
    conn = get_connection()
    try:
        transaction = load_transaction(transaction_id, conn=conn)

        history = get_user_history(transaction["user_id"], transaction["id"], conn=conn)
        yield _event("Checking user history...", data=history)

        chargebacks = check_previous_chargebacks(transaction["user_id"], conn=conn)
        yield _event("Checking previous chargebacks...", data=chargebacks)

        device = check_device(transaction["user_id"], transaction["device_id"], conn=conn)
        yield _event("Checking device...", data=device)

        merchant = check_merchant(transaction["merchant_id"], conn=conn)
        yield _event("Checking merchant...", data=merchant)

        risk = calculate_risk(transaction, history, device, merchant)
        yield _event("Calculating risk score...", data=risk)

        decision = decide(risk["score"])
        yield _event("Making decision...", data={"decision": decision, "score": risk["score"]})

        explanation = None
        source = None
        if include_explanation:
            explained = explain_risk(transaction, risk["score"], risk["signals"])
            explanation = explained["explanation"]
            source = explained["source"]
            yield _event("Generating explanation...", data=explained)

        result = {
            "transaction": transaction,
            "risk_score": risk["score"],
            "signals": risk["signals"],
            "decision": decision,
            "primary_driver": primary_driver(risk["signals"]) if decision == "REVIEW" else None,
            "explanation": explanation,
            "explanation_source": source,
            "chargebacks": chargebacks,
        }
        yield _event("Investigation complete.", result=result)
    finally:
        conn.close()
