"""TrustLayer FastAPI backend."""

from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.agents.orchestrator import investigate, score_transaction
from backend.database import get_connection

app = FastAPI(title="TrustLayer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/transactions")
def list_transactions() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                t.id,
                t.user_id,
                t.amount,
                t.currency,
                m.name AS merchant,
                t.timestamp,
                t.city,
                t.ground_truth
            FROM transactions t
            JOIN merchants m ON m.id = t.merchant_id
            ORDER BY t.timestamp DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


@app.get("/investigate/{transaction_id}")
def investigate_transaction(transaction_id: str) -> StreamingResponse:
    conn = get_connection()
    try:
        exists = conn.execute(
            "SELECT 1 FROM transactions WHERE id = ?",
            (transaction_id,),
        ).fetchone()
    finally:
        conn.close()
    if exists is None:
        raise HTTPException(status_code=404, detail=f"Unknown transaction: {transaction_id}")

    def event_stream():
        for event in investigate(transaction_id):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/stats")
def stats() -> dict:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                t.id, t.user_id, t.device_id, t.merchant_id, t.amount, t.currency,
                t.timestamp, t.city, t.country, t.ground_truth
            FROM transactions t
            """
        ).fetchall()
        decisions = {"ALLOW": 0, "REVIEW": 0, "BLOCK": 0}
        fraud_total = 0
        fraud_caught = 0
        trap_total = 0
        trap_allowed = 0
        for row in rows:
            txn = dict(row)
            scored = score_transaction(txn, conn=conn)
            decision = scored["decision"]
            decisions[decision] += 1
            if txn["ground_truth"] == "fraud":
                fraud_total += 1
                if decision in {"BLOCK", "REVIEW"}:
                    fraud_caught += 1
            elif txn["ground_truth"] == "trap":
                trap_total += 1
                if decision == "ALLOW":
                    trap_allowed += 1
        fraud_missed = fraud_total - fraud_caught
        trap_flagged = trap_total - trap_allowed
        return {
            "total_transactions": len(rows),
            "allow_count": decisions["ALLOW"],
            "review_count": decisions["REVIEW"],
            "block_count": decisions["BLOCK"],
            "fraud_transaction_count": fraud_total,
            "trap_transaction_count": trap_total,
            "fraud_caught": fraud_caught,
            "fraud_missed": fraud_missed,
            "trap_correctly_allowed": trap_allowed,
            "trap_incorrectly_flagged": trap_flagged,
            "fraud_caught_rate": round(fraud_caught / fraud_total, 4) if fraud_total else None,
            "trap_allowed_rate": round(trap_allowed / trap_total, 4) if trap_total else None,
        }
    finally:
        conn.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=False)
