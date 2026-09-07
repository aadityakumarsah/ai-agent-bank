# Services (marketplace)

The service directory under `/api/v1/services` demonstrates autonomous
commerce: discover → request → pay → call with proof. All demo-gated.

## `GET /api/v1/services`

List catalog (7 demo listings seeded while `DEMO_MODE`). Each item: `id`, `name`,
`category`, `endpoint`, `wallet_address` (a registry recipient name), `price`,
`currency`, `requires_payment`, `active`, `risk_level`, `is_demo`.

## `GET /api/v1/services/{service_id}`

One listing.

## Request → Pay → Call

**1. Request**
```bash
POST /api/v1/services/{service_id}/request   # {"agent_id": 12}
```
Free services answer `{"status":"ok","data":…,"http_status_hint":200}`.
Paid services answer `payment_required`:

```json
{
  "status": "payment_required",
  "http_status_hint": 402,
  "x402_note": "Simplified demo — not wire-compatible with real x402.",
  "payment_info": { "amount": 0.02, "currency": "USDC", "recipient": "Solana RPC Provider",
                    "category": "compute", "endpoint": "/v1/rpc" }
}
```

**2. Pay**
```bash
POST /api/v1/services/{service_id}/payment   # {"agent_id": 12}
```
Runs the shared `payment_flow` (idempotency → policy → balance → execution).
Results: `paid` | `blocked` | `approval_required` | `failed`, each with the
`checks` array and the transaction.

**3. Call with proof**
```bash
POST /api/v1/services/{service_id}/result    # {"agent_id": 12, "proof": {"tx_hash": "mock_…"}}
```
Finds the most recent executed payment for this service, validates the proof,
returns `{"data": …, "proof": {"verified": true, …}}`. Rate-limited:
`payment_limiter` (30/min).

## One-call demos

```bash
POST /api/v1/services/demo/killer    # find best RPC provider → $0.02 auto-payment
POST /api/v1/services/demo/failed    # $50 data buy vs $20 cap → blocked, $0 moved
```

These orchestrate the full flow and return a frame-by-frame trace. Both
rate-limited (`demo_limiter`, 20/min) and simulated.

## Idempotency

Payments carry `mkt:{agent_id}:{service_id}:{amount}` as the idempotency key.
Re-submitting returns `already_processed=true` with the existing transaction —
never a second payment.

> [!NOTE]
> These listings are demo scaffolds (`is_demo: true`), never fake payable
> endpoints — the responses are honest demo data behind real policy-gated
> execution. See [Service payments](/payments/marketplace) and
> [x402](/payments/x402).

Next: [LLM keys](/api/llm-keys).