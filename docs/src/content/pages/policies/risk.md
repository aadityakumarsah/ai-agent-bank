# Risk scoring

Alongside hard policy decisions, every notable payment context can be scored with
a deterministic, **rule-based** risk engine (`backend/app/services/risk_engine.py`).

> [!NOTE]
> This is not a machine-learning model and the code says so. It is an additive,
> transparent scoring function: every point a transaction receives is explained by
> a human-readable factor line in the response.

## The score

A transaction scores **0–100**, bucketed into three bands:

| Band | Score |
|---|---|
| `low` | 0–30 |
| `medium` | 31–70 |
| `high` | 71–100 |

## The factors

| Factor | Points | Driver |
|---|---|---|
| Amount | 0–35 | size relative to typical spend: ≤ $2 → 0, ≤ $20 → 10, ≤ $100 → 25, > $100 → 35 |
| Recipient trusted | 0 / 25 | not whitelisted / unknown → 25 |
| Merchant known | 0 / 5 | no known merchant record → 5 |
| Category allowed | 0 / 15 | not in policy allow-list → 15 |
| Contract interaction | 0 / 10 | arbitrary contracts blocked → 10 |
| Agent age | 0–15 | < 1h → 15, < 24h → 10, < 7d → 5, else 0 |
| Recent spending | 0–20 | daily budget utilization ≥ 90% → 20, ≥ 50% → 10, else 0 (no daily limit → 10) |
| Velocity | 0–15 | tx in the last hour: ≤ 2 → 0, ≤ 5 → 5, ≤ 10 → 10, more → 15 |
| Violation history | 0–20 | count of recent policy blocks: 0 → 0, 1 → 8, ≤ 3 → 14, more → 20 |

The maximum possible is 160, but the score is clamped to 0–100. Each evaluation
returns the full list of factors with their points and explanations, so you can
always see *why* a score is what it is.

## Example result

```json
{
  "score": 45,
  "level": "medium",
  "factors": [
    { "name": "Amount", "points": 10, "detail": "moderate amount (<= $20)" },
    { "name": "Recipient trusted", "points": 0, "detail": "recipient is whitelisted" },
    { "name": "Agent age", "points": 10, "detail": "agent is younger than 24 hours" },
    { "name": "Velocity", "points": 15, "detail": "very high velocity" },
    { "name": "Violation history", "points": 10, "detail": "repeated policy violations" }
  ]
}
```

## Where risk fits today

Risk scoring is computed from deterministic, server-side inputs and returned to
the client for transparency. It is currently **advisory** — policy decisions come
from the hard check list in the [policy engine](/policies/engine) — and its
inputs (velocity, violation history) also feed other controls like the
transaction ledger's stored score. The roadmap treats using the score as a
decision input (e.g. extra approval gates) as an extension point.

Next: [Payments overview](/payments/overview).