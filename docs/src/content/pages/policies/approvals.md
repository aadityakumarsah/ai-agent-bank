# Human approvals

Not every decision is the engine's to make. Set `require_approval_above` on a
policy and payments above that threshold pause and wait for a human.

## When do payments need approval?

Check 9 of the engine: if `amount > require_approval_above`, the engine returns
`requires_approval=true` (with `allowed=false`). The API records the transaction
as status **`approved`** — meaning *paused awaiting the human* — and no money
moves.

```json
{
  "run_id": 4,
  "status": "waiting_for_approval",
  "approval_required": true,
  "result": "APPROVAL REQUIRED\nRequested: $75\nPolicy: Transaction above $20 requires human approval.",
  "transaction": { "id": 9, "status": "approved", "amount": 75 }
}
```

## Where you approve

- **Approvals page** in the dashboard lists every paused payment.
- **Agent → Task Runner** shows and acts on the same pending payment.
- Both call the same endpoints: `POST …/transactions/{id}/approve` and
  `POST …/transactions/{id}/reject`.

Approving executes the payment **through the exact same guarded path** as an
auto-approved one: balance check → limits re-check → USDC transfer → ledger +
audit (`TRANSACTION_APPROVED` → `TRANSACTION_EXECUTED`). Rejecting simply marks
the transaction `rejected` with `"Rejected by the human. No money moved."` and
audits `TRANSACTION_REJECTED`.

## Idempotent and safe

- Approving an already-executed payment is a **no-op** (never double-pays).
- Rejecting an already-rejected/failed payment returns its current state.
- You cannot approve an executed payment, and you cannot reject one either.
- You cannot approve a `rejected`/`failed` payment (`409`).
- If the agent was suspended or killed in the meantime, approve returns `403`.

## The approval is real, not cosmetic

The 10-part build deliberately made the approval decision end-to-end real rather
than simulated in the UI. The paused transaction is a real ledger row; the
approve mutation executes a real (mock or devnet) USDC payment.

> [!IMPORTANT]
> Approval in the app is **unconditional once clicked** — the human is asked to
> review, and if they approve, the engine executes. There is no additional
> threshold inside the approval action itself (that is the point of the policy).

Next: [Risk scoring](/policies/risk).