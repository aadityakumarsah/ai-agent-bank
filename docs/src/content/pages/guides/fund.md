# Fund an agent & manage balances

An agent spends only what a human funds. This guide walks through funding in both
modes, then how to read balances.

## Mock mode (instant)

```bash
curl -s -X POST localhost:8000/api/v1/users/{wallet}/agents/1/fund \
  -H 'content-type: application/json' -d '{"amount": 500}'
```

```json
{ "mode": "mock", "simulated": true, "tx_hash": "mock_fund_…", "agent": { "id": 1, "balance": 500 } }
```

The ledger credits the balance immediately; audit logs `agent_funded`. Nothing
touches a chain.

## Real mode (reviewable USDC payment)

The same endpoint returns a **payment request** instead of a ledger credit:

```json
{
  "mode": "solana",
  "simulated": false,
  "payment_request": {
    "request_id": "…", "network": "devnet", "mint": "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU",
    "from_address": "your wallet", "to_address": "agent escrow", "to_ata": "…",
    "amount": 500.0, "currency": "USDC", "decimals": 6,
    "fee": { "fee_sol": 0.000005, "fee_lamports": 5000, "currency": "SOL", "estimated": true }
  }
}
```

Then, from your wallet:

1. Approve/connect your devnet wallet in the dashboard (or do it yourself in
   Phantom/Backpack on devnet).
2. Sign the `TransferChecked` USDC transfer into the agent's escrow ATA using the
   request details.
3. Confirm with the signature:

```bash
curl -s -X POST localhost:8000/api/v1/users/{wallet}/agents/1/fund/confirm \
  -H 'content-type: application/json' -d '{"amount": 500, "signature": "5X…"}'
```

Success returns the funded agent with the new `balance`.

## The funding invariant

Funding and spending are different actions with different routes. `fund` and
`confirm` are **human-owner** operations (wallet-scoped); `execute`/`pay` are the
**agent's** money-moving path and always policy-gated. Withdrawals back to a
human wallet are blocked by default (`blocked_withdrawals`), so a "fund then
drain" round-trip is refused by the engine.

## Reading balances

- `GET /api/v1/users/{wallet}/agents` returns each agent with `balance` and
  `total_spent`.
- `GET /api/v1/users/{wallet}/transactions` returns payments; in real mode the
  on-chain escrow must be funded before spending or execution fails with
  *"agent has insufficient funds"*.
- The dashboard shows balance per agent and across the wallet.

> [!IMPORTANT]
> Funds live on your agent's devnet escrow, not "in the app". If you reset the
> devnet ledger or move RPCs, on-chain holdings are unaffected — but only a
> policy-approved payment path can ever move them.

Next: [Configure an agent policy](/guides/policy).