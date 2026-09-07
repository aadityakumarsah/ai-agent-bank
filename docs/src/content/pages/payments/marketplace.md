# Service payments

The **service directory** is a marketplace of payable services an agent can
discover and buy autonomously — the demo of agent-to-agent commerce.

## The directory

Seeded in demo mode with **7 demo listings**, each with a name, category,
endpoint, recipient `wallet_address`, price in USDC, and risk level:

| Service | Category | Price | Risk |
|---|---|---|---|
| Solana RPC API | `compute` | $0.02 | low |
| Web Search API | `api` | $0.05 | low |
| Premium Data API | `data` | $50.00 | high |
| Image Generation API | `ai_model` | $0.10 | medium |
| Compute Provider | `compute` | $0.40 | medium |
| Vector Storage | `storage` | $0.03 | low |
| Peer Agent Service | `other_agent` | $0.25 | medium |

Every listing is flagged `is_demo=true` and returns a **DEMO SERVICE** response —
the marketplace never fakes a real payable endpoint.

```json
{
  "id": 1,
  "name": "Solana RPC API",
  "category": "compute",
  "endpoint": "/v1/rpc",
  "wallet_address": "rpcProvider",
  "price": 0.02,
  "currency": "USDC",
  "requires_payment": true,
  "active": true,
  "risk_level": "low",
  "is_demo": true
}
```

## The purchase flow

`POST /services/{service_id}/request` (`{agent_id}`) starts the flow:

1. **Request** → the service answers `status: "payment_required"` with
   `payment_info` (amount, currency, recipient, category, endpoint) — an
   **HTTP 402 in spirit** (see [x402](/payments/x402)).
2. **Pay** → `POST /services/{service_id}/payment` (`{agent_id,
   requested_amount?}`). The amount passes through `payment_flow`: idempotency
   check, policy evaluation, approval gate, balance check, execution. Result is
   one of `paid`, `blocked`, `approval_required`, or `failed`, always with the
   full `checks` list and the transaction.
3. **Call with proof** → `POST /services/{service_id}/result` (`{agent_id,
   proof: {tx_hash}}`). The endpoint finds the most recent executed payment to
   this service, validates the proof, and returns the (demo) API response.

Buying is **autonomous but never uncontrolled** — the policy gate is exactly the
same one every other payment passes.

## One-call demos

For live demos, two orchestrated endpoints run the whole flow and return a
frame-by-frame trace:

- `POST /services/demo/killer` — "Find the best Solana RPC provider and recommend
  it" ($0.02, auto-approved).
- `POST /services/demo/failed` — agent tries a $50 data purchase against a $20
  per-tx cap → blocked, $0 moved.

Both are rate-limited (`demo_limiter`: 20/min) and labelled simulated.

> [!NOTE]
> The same flow powers the **One-click Demos** tab, which reuses identical code
> paths (see [demo scenarios](/guides/scenarios)). Reviews of the flow should
> read `marketplace.py` alongside `payment_flow.py` — they share every helper.

Next: [x402 integration](/payments/x402).