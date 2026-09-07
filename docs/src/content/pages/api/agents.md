# Agents

All agent endpoints live under `/api/v1/users/{wallet}/agents`.

## Create

```bash
POST /api/v1/users/{wallet}/agents
{"name":"MyAgent","description":"pays for market data"}
```

Returns the agent with `status: "active"`, `balance: 0`, `total_spent: 0`, and a
derived `escrow_address`. **No policy is created** — the agent cannot pay until
one is set.

## List & get

```bash
GET  /api/v1/users/{wallet}/agents
GET  /api/v1/users/{wallet}/agents/{agent_id}
```

```json
{
  "id": 12, "name": "ResearchBot", "description": "…", "balance": 499.93,
  "total_spent": 0.07, "status": "active",
  "escrow_address": "5TviJ…",
  "policies": { "…": "the single policy for this agent" },
  "created_at": "2026-09-01T10:00:00Z"
}
```

## Policy

```bash
POST /api/v1/users/{wallet}/agents/{agent_id}/policy    # set
PUT  /api/v1/users/{wallet}/agents/{agent_id}/policy    # update (audited policy_changed)
```

Body shape (see [Policies](/core/policies) for semantics):

```json
{
  "max_per_transaction": 20, "max_per_day": 100, "max_per_month": 1000,
  "allowed_categories": ["api","compute","data"],
  "blocked_human_transfers": true, "blocked_withdrawals": true,
  "blocked_arbitrary_contracts": true, "require_approval_above": 10,
  "allowed_recipient_addresses": []
}
```

## Funding

```bash
POST /api/v1/users/{wallet}/agents/{agent_id}/fund            # {"amount": 500}
POST /api/v1/users/{wallet}/agents/{agent_id}/fund/confirm    # {"amount": 500, "signature": "5X…"}  (real mode)
```

In mock mode `fund` immediately credits the ledger (`mode:"mock"`,
`simulated:true`, `tx_hash:"mock_…"`). In real mode it returns a **payment
request** you sign in your wallet, then `fund/confirm` settles it and fires
`AGENT_FUNDED`. Full details in [Funding & payment requests](/payments/funding).

## Lifecycle status

```bash
PUT /api/v1/users/{wallet}/agents/{agent_id}/pause
PUT /api/v1/users/{wallet}/agents/{agent_id}/resume
```

`pause` → `suspended`; `resume` → `active`. A suspended agent refuses new task
runs and the engine's "Agent active" check fails every payment. Killed/revoked
agents cannot be resumed — see [Kill switch](/security/kill).

## Runs

```bash
POST /api/v1/users/{wallet}/agents/{agent_id}/runs   # {"task": "…"}
```

Documented fully under [Task runs](/api/runs).

> [!NOTE]
> There is no endpoint to withdraw or delete an agent. Withdrawals are blocked by
> default (`blocked_withdrawals`), and deletes would orphan the escrow — plan
> around this when automating agent lifecycle.

Next: [Transactions](/api/transactions).