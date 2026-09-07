# Funding & payment requests

An agent can only spend what it has been funded with. Funding is a
human-initiated act and, in real mode, it is a **reviewable USDC payment** from
the owner's wallet into the agent's escrow.

## `POST …/agents/{id}/fund`

```bash
curl -s -X POST localhost:8000/api/v1/users/{wallet}/agents/4/fund \
  -H 'content-type: application/json' -d '{"amount": 500}'
```

### Mock mode

Returns a `FundMockResult` — a simulated ledger credit (`tx_hash: "mock_…"`) and
the updated agent. Nothing touches a chain.

```json
{
  "mode": "mock",
  "simulated": true,
  "tx_hash": "mock_fund_2f9a…",
  "agent": { "id": 4, "balance": 500.0, "status": "active" }
}
```

### Real mode

Returns a `FundSolanaResult` with a full **payment request** the frontend turns
into a wallet transaction the owner signs. The backend verifies the fee estimate
against the RPC before agreeing to the transfer.

```json
{
  "mode": "solana",
  "simulated": false,
  "agent_id": 4,
  "agent_name": "ResearchBot",
  "payment_request": {
    "request_id": "…",
    "mode": "solana",
    "network": "devnet",
    "simulated": false,
    "from_address": "owner-wallet-address",
    "to_address": "5TviJ…",
    "to_ata": "Ata1…",
    "amount": 500.0,
    "currency": "USDC",
    "mint": "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU",
    "decimals": 6,
    "fee": { "fee_sol": 0.000005, "fee_lamports": 5000, "currency": "SOL", "estimated": true }
  }
}
```

The dashboard then:

1. lists the agent's escrow / ATA;
2. asks your wallet to `signAndSendUsdcTransfer` with the payment-request details;
3. calls `POST …/agents/{id}/fund/confirm` with `{"amount": …, "signature": …}`;
4. on success returns the funded agent.

## `POST …/agents/{id}/fund/confirm`

```bash
curl -s -X POST localhost:8000/api/v1/users/{wallet}/agents/4/fund/confirm \
  -H 'content-type: application/json' -d '{"amount": 500, "signature": "5X9q…"}'
```

This records the funding transaction in the ledger and audit trail
(`AGENT_FUNDED`), and updates the agent balance.

> [!TIP]
> A demo wallet (`DemoWallet11111111111111111111111111111111`) and three seeded
> agents exist out of the box in demo mode, so you can see a funded dashboard
> without signing anything. For real devnet funding, see
> [Fund an agent](/guides/fund) and [Go live on devnet](/guides/realmode).

Next: [Transaction ledger](/payments/ledger).