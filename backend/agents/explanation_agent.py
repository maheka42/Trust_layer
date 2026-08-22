"""Short risk explanations via Groq, with a local fallback."""

from __future__ import annotations

import os


def _local_explain(transaction: dict, score: int, signals: list[dict]) -> str:
    decision = "ALLOW" if score < 30 else "REVIEW" if score <= 70 else "BLOCK"
    if not signals:
        return (
            f"Score {score} leads to {decision} because no risk points were added "
            "from amount, device, merchant, time, or location."
        )
    parts = [str(item.get("description", "")).rstrip(".") for item in signals if item.get("description")]
    joined = "; ".join(parts)
    return f"Score {score} leads to {decision} because {joined}."


def explain_risk(transaction: dict, score: int, signals: list[dict]) -> dict:
    fallback = _local_explain(transaction, score, signals)
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        return {"explanation": fallback, "source": "local_fallback"}

    try:
        from groq import Groq

        client = Groq(api_key=api_key)
        signal_lines = "\n".join(
            f"- {item.get('name')}: {item.get('description')} (weight {item.get('weight')})"
            for item in signals
        ) or "- none"
        prompt = (
            "Explain this payment risk score in 1-2 sentences. "
            "Use only the signals below. Do not invent facts, merchants, cities, or amounts "
            "that are not present in the signals.\n"
            f"Score: {score}\n"
            f"Signals:\n{signal_lines}"
        )
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0.2,
            max_tokens=120,
            messages=[{"role": "user", "content": prompt}],
        )
        text = (response.choices[0].message.content or "").strip()
        if not text:
            return {"explanation": fallback, "source": "local_fallback"}
        return {"explanation": text, "source": "groq"}
    except Exception:
        return {"explanation": fallback, "source": "local_fallback"}
