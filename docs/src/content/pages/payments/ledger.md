# Transaction ledger

Every attempted payment is a first-class row in the `transactions` table
(`backend/app/db/models.py`), from creation to settlement. The ledger is the
source of truth the dashboard, approvals page, and audit trail all read.

## States

| `status` | Meaning |
|---|---|
| `pending` | created, not yet evaluated/executed |
| `approved` | **paused awaiting human approval** (call it "Approval required" in the UI) |
| `rejected` | blocked by policy or rejected by the human — zero USDC moved |
| `executed` | settled (mock or real) and fully in the ledger |
| `failed` | execution refused (insufficient balance, limit at execution time, provider error) |

## Columns that matter

| Column | Purpose |
|---|---|
| `idempotency_key` | unique; the double-submit guard |
| `tx_hash` | `mock_…` in mock mode, on-chain signature in real mode |
| `rejection_reason` | why a payment was blocked or failed (`null` otherwise) |
| `risk_score` / `risk_level` | stored deterministic [risk score](/policies/risk) snapshot |
| `executed_at` | when it settled (nil until it does) |
| `category` / `recipient_*` | the auditable intent of the payment |

`transaction_type` is `payment` for all present-day flows (`withdrawal` exists as
a labelled type; withdrawals are **blocked** by default policy).

## Idempotency

Keys are derived per flow:

- **Marketplace:** `mkt:{agent_id}:{service_id}:{amount}` (or an explicit key).
- **Demo scenarios:** `demo:{scenario_id}:{client_request_id}`.
- **Task runs:** the runtime creates a fresh pending transaction per run and
  executes through the same dedupe path.

Because the key is unique, retries return the existing row instead of a new
payment. `create_or_get_tx` returns `created=false` on a hit and callers **must
not** execute twice — the marketplace and scenarios honour this.

## Read paths

```text
GET  /api/v1/users/{wallet}/transactions            list (newest first)
GET  /api/v1/users/{wallet}/transactions/{tx_id}    one transaction
POST /api/v1/users/{wallet}/transactions/{tx}/approve|reject   human actions
POST /api/v1/demo/check                             evaluate a synthetic payment
```

Every state change is mirrored into the **audit trail**
(`TRANSACTION_REQUESTED`, `TRANSACTION_APPROVED`, `TRANSACTION_DENIED`,
`TRANSACTION_EXECUTED`, `TRANSACTION_REJECTED`, `TRANSACTION_CANCELLED`) and into
`TransactionLog` rows attached to the transaction itself.

> [!IMPORTANT]
> "Approved" is a **hold**, not a settle. In this UI an `approved` transaction
> is one you still have to approve from the Approvals page; `executed` is the
> money actually moving.

Next: [Service payments](/payments/marketplace).