# Create your first agent

The fastest way to see the whole loop is the dashboard, but the same steps work
almost entirely through the API. This guide assumes the backend is running on
`:8000` (see [Install](/get-started/install)).

## 1. Register a wallet

```bash
curl -s -X POST localhost:8000/api/v1/users \
  -H 'content-type: application/json' -d '{"wallet_address":"MyWallet123"}'
```

The response is a `User` with an `id`. You use the wallet address as your route
scope for everything that follows.

## 2. Create an agent

```bash
curl -s -X POST localhost:8000/api/v1/users/MyWallet123/agents \
  -H 'content-type: application/json' \
  -d '{"name":"MyAgent","description":"pays for market data"}'
```

You get back the agent with `status: "active"`, `balance: 0`, and a derived
`escrow_address`. **Note the agent has no policy yet** — it cannot pay anything.

## 3. Give it a policy

```bash
curl -s -X POST localhost:8000/api/v1/users/MyWallet123/agents/1/policy \
  -H 'content-type: application/json' -d '{
    "max_per_transaction": 20,
    "max_per_day": 100,
    "max_per_month": 1000,
    "allowed_categories": ["api","compute","data"],
    "blocked_human_transfers": true,
    "blocked_withdrawals": true,
    "blocked_arbitrary_contracts": true,
    "require_approval_above": 10
  }'
```

The `policy_changed` audit event fires. The engine now has its rules.

## 4. Fund it

```bash
curl -s -X POST localhost:8000/api/v1/users/MyWallet123/agents/1/fund \
  -H 'content-type: application/json' -d '{"amount": 500}'
```

In mock mode you get a ledger credit (`mode: "mock"`, `simulated: true`,
`tx_hash: "mock_…"`) — instant. In real mode you get a
[payment request](/payments/funding) to sign in your wallet, then confirm it.

## 5. Run a task

```bash
curl -s -X POST localhost:8000/api/v1/users/MyWallet123/agents/1/runs \
  -H 'content-type: application/json' -d '{"task":"Test the RPC provider"}'
```

The run traces propose → evaluate → decide → execute, and the result includes the
transaction, every policy check, and the mode label.

> [!TIP]
> Already funded and configured in demo mode? The three seeded demo bots
> (ResearchBot, ComputeBot, DataBot) are ready to task immediately — ask one to
> "test the RPC API" and watch a fully-labelled `$0.02` mock payment execute.

Next: [Fund an agent & manage balances](/guides/fund).