# Task runs

A run is one task execution with a fully-traced outcome.

## `POST /api/v1/users/{wallet}/agents/{agent_id}/runs`

```bash
curl -s -X POST localhost:8000/api/v1/users/{wallet}/agents/12/runs \
  -H 'content-type: application/json' \
  -d '{"task":"Test the Solana RPC provider and report cost"}'
```

### When the payment is auto-approved

```json
{
  "run_id": 1,
  "status": "completed",
  "blocked": false,
  "result": "Payment executed: $0.02 to Solana RPC Provider (compute). Tx: mock_…",
  "decision": {
    "allowed": true,
    "requires_approval": false,
    "reason": "",
    "checks": [ { "name": "Agent active", "passed": true, "detail": "active" }, "…" ]
  },
  "transaction": {
    "id": 8, "status": "executed", "amount": 0.02, "category": "compute",
    "recipient": "Solana RPC Provider", "tx_hash": "mock_…",
    "mode": "mock", "simulated": true
  }
}
```

### When approval is required

```json
{
  "run_id": 4,
  "status": "waiting_for_approval",
  "result": "APPROVAL REQUIRED\nRequested: $75\nPolicy: Transaction above $20 requires human approval.",
  "transaction": { "id": 9, "status": "approved", "amount": 75 }
}
```

### When the engine blocks

```json
{
  "run_id": 5,
  "status": "completed",
  "blocked": true,
  "result": "Payment blocked: [recipient_trust] Recipient 'evil' is unknown. Human transfers are disabled.",
  "decision": { "allowed": false, "requires_approval": false, "checks": [ { "name": "Recipient trust", "passed": false } ] }
}
```

## Result shape contract

| Field | Meaning |
|---|---|
| `run_id` | the run id (also useful as an idempotency anchor) |
| `status` | `completed` / `waiting_for_approval` / `failed` (running is transient) |
| `blocked` | engine refused (`allowed=false` without approval need) |
| `decision` | full policy decision incl. every check |
| `transaction` | the affected ledger row, when one was created |
| `result` | human-readable trace tail |

A stopped agent (suspended/killed) refuses runs before any transaction exists
(`403` style refusal via the engine state check), and runs against a mock setup
still return `mode:"mock"`/`simulated:true`.

> [!TIP]
> `blocked` is a quick signal for automated tests: `assert not result["blocked"]`
> after a successful execution.

Related: [Tasks & task runs](/core/tasks) · [Run one](/guides/task).