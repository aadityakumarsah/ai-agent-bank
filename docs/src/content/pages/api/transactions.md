# Transactions

The ledger for a wallet lives under `/api/v1/users/{wallet}/transactions`.

## List

```bash
GET /api/v1/users/{wallet}/transactions
```

Newest first. Each row carries the status, amount, direction (`in`/`out`),
recipient, category, idempotency key, `tx_hash`, `mode`, `simulated`, and the
risk snapshot (`risk_score`, `risk_level`).

## Get one

```bash
GET /api/v1/users/{wallet}/transactions/{tx_id}
```

## Human actions

```bash
POST /api/v1/users/{wallet}/transactions/{tx_id}/approve
POST /api/v1/users/{wallet}/transactions/{tx_id}/reject
```

These act on the `approved` state — a payment paused at the approval threshold.

| Action | Result |
|---|---|
| approve (paused) | executes through the guarded path → `executed` |
| approve (already executed) | **no-op**, returns state (never double-pays) |
| approve (rejected/failed) | `409` conflict |
| reject | marks `rejected`; zero USDC moved |
| approve when agent killed | `403` |

## The state machine in one table

```
pending ──→ rejected     (policy / human rejection)
   │
   ├──→ approved ──→ executed   (auto or human-approved with balances)
   │
   └──→ failed                  (execution refusal: funds, caps, provider)
```

- `approved` = **paused awaiting human** (*not* settled).
- `rejected` = evaluated and refused.
- `failed` = refused **at execution** (insufficient balance, daily/monthly cap at
  execution time, provider error).

## Status + reason

Blocked and failed rows explain themselves:

```json
{
  "id": 41,
  "status": "rejected",
  "amount": 50,
  "rejection_reason": "Transaction exceeds per-transaction limit. Requested $50 but allowed $20.",
  "checks": [
    { "name": "Per-transaction limit", "passed": false, "requested": "50", "allowed": "20" }
  ],
  "mode": "mock",
  "simulated": true
}
```

> [!IMPORTANT]
> Read `status` before writing logic: an `approved` row is a **hold**, not a
> settlement. Treat `executed`, `mode`, and `simulated` as the money-truth
> fields.

Related: [Transaction ledger](/payments/ledger) · [Approvals](/guides/approvals).