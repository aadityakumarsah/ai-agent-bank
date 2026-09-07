# Approve or reject payments

When a payment exceeds a policy's approval threshold it does **not** execute. It
stops in the `approved` state — paused — and waits for you.

## Recognizing a paused payment

- Dashboard **Approvals** page lists every one, newest first.
- The agent's **Task Runner** shows `waiting_for_approval` and the pending
  transaction's full proposal for review.
- Its `status` is `approved` (recorded when the engine returned
  `requires_approval: true`), and the ledger shows **no money moved yet**.

## The action

**Approve** — `POST /api/v1/users/{wallet}/transactions/9/approve`

Runs the exact same guarded path as any auto-approved payment: balance check →
daily/monthly limits re-checked → USDC transfer → ledger + audit
(`TRANSACTION_APPROVED`, then `TRANSACTION_EXECUTED`).

**Reject** — `POST /api/v1/users/{wallet}/transactions/9/reject`

Marks the transaction `rejected` with *"Rejected by the human. No money moved."*
and audits `TRANSACTION_REJECTED`.

## Safety rails

- Approving an **already-executed** payment is a **no-op** — never double-pays.
- You **cannot** approve a `rejected` or `failed` payment (`409`).
- Rejecting an already-rejected payment returns its state; no error loop.
- If the agent got suspended or killed while paused, approval returns `403`.
- If the balance ran out on chain, approval **fails cleanly** — *"Fund the agent
  and approve again"* — and the payment stays paused.

## Approving vs. policy

Approving does **not** rewrite policy. It settles this one payment (within the
re-checked limits). If you want *future* payments of that size to auto-execute,
raise `require_approval_above` via the agent's policy — that's a separate,
audited change.

> [!IMPORTANT]
> An approval is final and moves money (mock or real, always labelled). The UI
> shows the pending amount, recipient, and mode clearly before you confirm —
> review before clicking.

Related: [Human approvals](/policies/approvals) · [Transaction ledger](/payments/ledger).