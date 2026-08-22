# TrustLayer

Payment fraud systems often hide their reasoning. Analysts see a score, not why a charge was blocked, sent to review, or allowed. That makes disputes hard to audit and makes “unusual but legitimate” activity look like an attack.

TrustLayer is an explainable, agentic transaction risk investigation system. For a selected payment it gathers user history, device, merchant, and chargeback context, applies a transparent rule-based score, issues ALLOW / REVIEW / BLOCK, and streams a short explanation of the points that were actually added.

## Architecture

```
Transaction
    ↓
History Agent
    ↓
Device Agent
    ↓
Merchant Check
    ↓
Explainable Risk Engine
    ↓
Decision
    ↓
Explanation Agent
```

The risk engine is intentionally rule-based/statistical rather than a trained ML classifier. This prototype uses synthetic data and prioritizes transparent, auditable reasoning over opaque model output.

## Prerequisites

- Python 3.11+
- `seed_data.db` in the project root (created by the generator below)

## Installation

From the project root:

```
python -m pip install -r backend/requirements.txt
```

Required packages: `fastapi`, `uvicorn`, `groq`. Groq is optional at runtime. If `GROQ_API_KEY` is missing or the API fails, TrustLayer uses a deterministic local explanation built only from triggered signals.

## Generate synthetic data

```
python backend/data_generator.py
```

This creates `seed_data.db` with 50 users, 500–800 transactions (about 70% normal, 20% injected fraud, 10% legitimate unusual traps), devices, merchants, and a small set of historical chargebacks. Re-running the generator recreates the database so records are not duplicated. Seed: `random.seed(42)`.

## Start backend

From the project root:

```
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

API:

- `GET /transactions`
- `GET /stats`
- `GET /investigate/{transaction_id}` (SSE)

## Start frontend

Plain HTML/CSS/JS. No npm.

```
python -m http.server 5500 --directory frontend
```

## Open dashboard

Open [http://127.0.0.1:5500](http://127.0.0.1:5500)

The dashboard calls the backend at `http://127.0.0.1:8000`. If the API is down, it shows: `Backend unavailable. Start FastAPI at http://127.0.0.1:8000`.

## Demo flow

1. Confirm stats cards load (totals come from `/stats`, not invented numbers).
2. Browse the transaction table (ground truth is shown only for demo visibility; it is not used to compute risk).
3. Click **Investigate** on a row.
4. Watch the live SSE log:
   - Checking user history...
   - Checking previous chargebacks...
   - Checking device...
   - Checking merchant...
   - Calculating risk score...
   - Making decision...
   - Generating explanation...
   - Investigation complete.
5. Read the score, ALLOW / REVIEW / BLOCK badge, per-signal points, and explanation source (Groq LLM or local fallback).

Suggested IDs from the generated `seed_data.db` (do not treat these as production labels):

| Demo | ID | Why it is useful |
|---|---|---|
| Clear fraud → BLOCK | `txn_0339` | Injected fraud: high amount at NightOwl Adult Shop, 01:46, city mismatch. Score 72. |
| Suspicious → REVIEW | `txn_0001` | Injected fraud: GiftCard Galaxy, 4.1x average, 03:00, Sao Paulo vs home New York. Score 61. |
| Legitimate normal → ALLOW | `txn_0003` | Typical grocery/transit-style spend in the user’s home city with no added risk points. Score 0. |
| Legitimate unusual trap → ALLOW | `txn_0208` | Injected trap: Summit Electronics in another city, elevated amount, still under 30. Score 27. |

## Risk scoring weights

Maximum contribution per factor (total 100):

| Factor | Max points |
|---|---|
| Amount anomaly | 35 |
| New device | 20 |
| Merchant risk | 20 |
| Unusual time | 15 |
| Location mismatch | 10 |

Amount anomaly scales with how far the charge is from the user’s historical average (1–2x low, 2–5x moderate, 5–10x high, >10x near maximum). Merchant points are reduced if the user has used that merchant before. Unusual time is strongest between 12 AM and 5 AM.

## Decision thresholds

- score **< 30** → ALLOW
- score **30–70** → REVIEW
- score **> 70** → BLOCK

## Synthetic evaluation metrics

`GET /stats` reports:

- `fraud_caught_rate`: injected synthetic fraud transactions that received BLOCK or REVIEW, divided by total injected fraud transactions
- `trap_allowed_rate`: injected synthetic legitimate unusual (trap) transactions that received ALLOW, divided by total trap transactions

These are **not** real-world fraud detection accuracy metrics. They only describe how this rule engine behaves on the synthetic seed set. The dashboard labels them “Injected Fraud Patterns Caught” and “Legitimate Trap Transactions Allowed”.
