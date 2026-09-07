# Payments overview

Every payment in AI Agent Bank — from a task run, a marketplace purchase, a demo
scenario, or a human approval — goes down the **same guarded path**. There is no
second, faster, or unguarded route to move money.

## The path

```
proposal
  → create or find transaction (idempotency key)
  → policy engine (deterministic checks)
  → approval gate?  (pause → human approves/rejects)
  → balance check   (never let an underfunded agent pay)
  → execution guard (daily/monthly caps re-checked)
  → USDC transfer   (mock or Solana)
  → ledger + audit row
```

This lives in `backend/app/services/payment_flow.py`, and both the marketplace
and the demo scenarios import the same helpers — `create_or_get_tx`,
`evaluate_payment`, `mark_approval_required`, `mark_rejected`,
`attempt_execution`. Identical money behaviour everywhere is the design goal.

## Key invariants

1. **Policy first.** `attempt_execution` is only ever reached after the engine
   has approved. The runtime enforces this ordering.
2. **Idempotent.** Every money path carries an idempotency key (e.g.
   `mkt:{agent}:{service}:{amount}` or `demo:{scenario}:{client}`). A repeated
   submit returns the existing transaction; it never pays twice.
3. **Balance-checked.** An agent with insufficient balance gets a clean failure
   ("Fund the agent and approve again"), never a partial payment.
4. **Re-checked at execution.** Daily/monthly caps are re-verified in the same
   request that moves money.
5. **Audited.** Every attempt — approved, blocked, paused, executed — writes an
   audit event plus a ledger row.

## Mock vs real

The *same* path runs in both modes; only the transfer implementation differs:

| | Mock | Real |
|---|---|---|
| Implementation | `MockPaymentService` | `SolanaPaymentService` |
| Hash format | `mock_…` | on-chain signature |
| `mode` / `simulated` | `"mock"` / `true` | `"solana"` / `false` |
| Explorer link | none | `explorer.solana.com/tx/…` |
| Env requirement | none | `SOLANA_RPC_URL`, `SOLANA_PRIVATE_KEY`, `USE_REAL_PAYMENT=true` |

The payment service is selected at app start from the environment; both classes
expose the identical interface (`get_balance`, `create_payment_request`,
`estimate_fee`, `execute_payment`, `verify_transaction`, …).

> [!IMPORTANT]
> Money does not move twice. Idempotency keys are unique on the transaction
> table, and approvals of already-executed payments are no-ops.

Next: [USDC on Solana](/payments/usdc).