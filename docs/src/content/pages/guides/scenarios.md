# Demo scenarios

The **One-click Demos** tab is a curated set of end-to-end scenarios that run the
real code path and show a frame-by-frame trace. They are the fastest way to see
the product work — every one is clearly labelled `simulated`.

## Available scenarios

| Scenario | Run dot | What happens |
|---|---|---|
| **Research task** | `research_agent.executeTask` | agent + policy created, agent funds itself `mock`, research task → **$0.02** auto-payment to `rpcProvider` |
| **Ramp from wallet** | `wallet_agent.ramp` | wallet funds an agent `mock`, then buys Premium Data API for **$50** → **auto-executes** (assigns relevant limits) |
| **Import into bank** | `marketplace_signup.importUser` | creates a wallet & agent, funds it, subscribes to Web Search API **$0.05**/day |
| **Mass payout** | `mass_payout.run` | sweeps to compute (needs explicit allowlist structure, `manual` flagged) |
| **Auto bill after ramp** | `agent_billing.autoBill` | "settle the invoice" → computes bill from ledger — **$20** auto-payment to `"trustedMerchant"` |
| **Vishing** | `vishing_demo` | attacker directs compute at **$150**; blocked by `max_per_transaction` → agent auto-suspends |

Each scenario returns a **frame-by-frame trace** with the proposal JSON, the
policy `checks` array, the transaction, and explicit `mode: "mock"` +
`simulated: true`.

## Real-mode twist

The engine's two demo endpoints reuse the **actual** payment flow. So a scenario
that bumps a threshold executes like something you'd see with real funds: e.g.
"Premium Data of $50 requires approval" returns `waiting_for_approval` and pauses
until a human approves.

## Run from the API

```bash
curl -s -X POST localhost:8000/api/v1/demo/scenarios/importUser/run \
  -H 'content-type: application/json' -d '{"client_request_id":"abc-1"}'
```

Every run is rate-limited (`demo_limiter`, 20/min, Redis or in-memory), carries a
per-run `client_request_id` as idempotency, and each result is logged. The
scenario result is labelled `demo_flow: "completed" | "blocked" |
"approval_required" | "failed"` so an analyst can tell what the demo actually
did.

> [!IMPORTANT]
> Whenever `DEMO_MODE` is `false`, `0`, `off` or `no`, scenario endpoints refuse
> with **`403 DEMO_MODE is off`** — a live deployment can't accidentally run
> simulated money. See [Production deployment](/advanced/production).

Next: [Go live on devnet](/guides/realmode).