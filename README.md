# TrustLayer

TrustLayer is an explainable agentic risk manager built for the Razorpay AI Buildathon.

It investigates transactions using user history, device information, merchant risk, transaction timing, and location. It then calculates a transparent risk score and returns one of three decisions:

**ALLOW | REVIEW | BLOCK**

The system is designed to explain *why* a transaction was flagged instead of producing an unexplained fraud score.

## Live Demo

LINK: https://trust-layer-smoky.vercel.app


## How It Works

Transaction
→ History Check
→ Device Check
→ Merchant Check
→ Risk Engine
→ Decision
→ Explanation

The investigation progress is streamed live to the dashboard using Server-Sent Events (SSE).

## Risk Scoring

The risk score ranges from 0–100.

- Amount anomaly: up to 35 points
- Device risk: up to 20 points
- Merchant risk: up to 20 points
- Unusual time: up to 15 points
- Location mismatch: up to 10 points

Decision:

- 0–29: ALLOW
- 30–70: REVIEW
- 71–100: BLOCK

## Dataset

The prototype uses reproducible synthetic data.

- 50 users
- 689 transactions
- 110 devices
- 40 merchants
- 20 chargebacks
- 482 normal transactions
- 137 injected fraud transactions
- 70 legitimate unusual trap transactions

The trap transactions are intentionally unusual but legitimate and are used to test whether the system can avoid flagging every unusual transaction as fraud.

## AI Explanation

The risk score is calculated using transparent rules.

The LLM is used only to explain the calculated risk signals in simple language.

If the Groq API is unavailable, TrustLayer uses a local fallback explanation so the investigation can still complete.

## Tech Stack

- Python
- FastAPI
- SQLite
- HTML/CSS/JavaScript
- Server-Sent Events (SSE)
- Groq
- Render
- Vercel

## Project Structure

trustlayer/
├── backend/
│   ├── agents/
│   ├── main.py
│   ├── database.py
│   ├── data_generator.py
│   ├── models.py
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── style.css
├── seed_data.db
└── README.md
