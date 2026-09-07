# Agents

An **agent** is the spending entity a human creates and controls. It is a
database record with an id, name, description, a USDC balance, a derived
`escrow_address`, a single `Policy`, and a transaction history.

```json
{
  "id": 12,
  "name": "ResearchBot",
  "description": "Autonomous research assistant",
  "balance": 499.93,
  "total_spent": 0.07,
  "status": "active",
  "escrow_address": "5TviJ...",
  "policies": { "...": "see Policies" },
  "created_at": "2026-09-01T10:00:00Z"
}
```

## Agent statuses

| Status | Meaning | Can it transact? |
|---|---|---|
| `active` | Normal operation | Yes |
| `suspended` | Paused by the human | No — tasks and payments are refused |
| `killed` | Revoked permanently | No — cannot run tasks or pay; supersedes suspend |

The model also carries `revoked` as a legacy alias for `killed`. A status change
is a first-class, audited action (`AGENT_PAUSED` / `AGENT_RESUMED` /
`AGENT_REVOKED`).

## Creating an agent

```bash
curl -s -X POST localhost:8000/api/v1/users/{wallet}/agents \
  -H 'content-type: application/json' \
  -d '{"name":"MyAgent","description":"pays for market data"}'
```

An agent is created **active**, with a zero balance, and **no policy**. Until a
policy exists, the engine refuses every payment with
*"No policy configured for agent"* — an off-by-default guarantee.

## The escrow

Each agent owns a derived `escrow_address` generated server-side from the master
keypair (`SOLANA_PRIVATE_KEY`); the agent's secret key is never stored or
returned. Funding and payments happen against this address. See
[Agent wallets & escrow](/core/wallets) and [Private keys](/security/keys).

## What an agent controls

- **Balance** — USDC it has been funded with. Executed payments decrement it;
  `total_spent` accumulates.
- **Policy** — exactly one per agent.
- **Tasks** — the human can run a task (\`POST .../runs\`), which the runtime
  executes through the guarded payment path.
- **History** — transactions and audit events are scoped to the agent and its
  owner wallet.

> [!NOTE]
> The demo seed provisions three showcase agents under the demo wallet
> (`DemoWallet11111111111111111111111111111111`): **ResearchBot**
> ($20 / $100 / $1,000, approval ≥ $20), **ComputeBot**
> ($50 / $200 / $2,000, approval ≥ $100), and **DataBot**
> ($100 / $250 / $500, approval ≥ $50). Their history is clearly labelled with
> `mock_` hashes and is seeded only while `DEMO_MODE` is on.

Next: [Agent wallets & escrow](/core/wallets).