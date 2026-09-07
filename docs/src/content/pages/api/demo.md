# Demo endpoints

The `/api/v1/demo` namespace is for synthetic evaluation and the one-click
scenario runner. Everything here is gated by `DEMO_MODE` (403 when off) and
rate-limited, and money paths stay fully labelled.

## `POST /api/v1/demo/check`

Evaluate a synthetic payment against an agent's live policy without moving money:

```bash
curl -s -X POST localhost:8000/api/v1/demo/check \
  -H 'content-type: application/json' \
  -d '{"agent_id": 12, "amount": 75, "recipient": "rpcProvider",
       "recipient_name": "Solana RPC Provider", "category": "compute"}'
```

Returns the policy decision (`allowed`, `requires_approval`, `reason`,
`checks`), the risk snapshot, and a `simulated: true` marker. This is the
cheapest honest way to display "what would happen" in a proposal preview.

## Scenario runner

```bash
POST /api/v1/demo/scenarios/research/run
POST /api/v1/demo/scenarios/importUser/run
POST /api/v1/demo/scenarios/ramp/run
…  # request body: {"client_request_id": "…"}
```

Each runs the real code path (agent creation, funding, payments, sometimes
approvals) and returns a frame-by-frame trace, `demo_flow` label, and explicit
`mode:"mock" / simulated:true`. `client_request_id` feeds the idempotency key so
retries never double-run a scenario.

Available scenario keys include `research`, `wallet_ramp`, `marketplace_signup`,
`mass_payout`, `agent_billing`, `vishing`. See [Demo scenarios](/guides/scenarios
) for the run table, or `GET /api/v1/demo/scenarios` to enumerate what's live.

## `POST /api/v1/demo/scenarios` (preview)

```bash
POST /api/v1/demo/scenarios   # {"scenario_ids": ["research","vishing"], "client_request_id": "…"}
```

Preview endpoint for composing multiple scenario runs.

## Gate + limits

- `DEMO_MODE=false` → every `/demo/*` and scenario endpoint returns
  **`403 DEMO_MODE is off`**.
- `demo_limiter` (`20/min` over Redis or in-memory) applies to scenario and
  one-call demo endpoints.

> [!IMPORTANT]
> "One-click demos" and scenario runners mutate the demo ledger (agents, funding
> rows, executed mock transactions) — that's expected, but don't run them against
> a real deployment: the gate exists precisely so a production backend refuses.

Related: [Guide: run the demos](/guides/scenarios) · [Service demos](/api/services).