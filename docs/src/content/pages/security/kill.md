# Agent kill switch

Every agent can be **paused** or **killed** at any time from the Agents page.
These are the two human controls that bypass every other consideration — they are
the emergency brake.

## Pause (`suspend`)

- Target status: `suspended` (`is_active=false` in the UI).
- The policy engine refuses every further payment: *"Agent is suspended"*.
- Task runs are blocked before they can create a new transaction.
- Existing `approved` (paused) payments stay pending, waiting for your decision.
- Audited as `agent_paused`.

```bash
PUT /api/v1/users/{wallet}/agents/12/pause
```

There is also `agent_auto_suspended` — a path the code supports for automated
supervision, kept in the audit vocabulary.

## Resume

`PUT …/agents/12/resume` switches back to `active` (`agent_resumed`). Payments
work again. If things escalated to a kill, see below.

## Kill (`revoke`)

- Target status: `killed`. This is **permanent and one-way** — audit event
  `agent_revoked`.
- The engine's check #2 ("Agent active") fails for `killed` just as it does for
  `suspended`.
- Unlike suspension, the UI additionally frames it as a non-reversible removal —
  a killed agent cannot run tasks and cannot pay, with intent matching the
  "revoked" vocabulary used in the data model and errors.

## The speed of the brake

Because the policy engine is checked at the *start* of every money path, the
suspension/kill takes effect on the very next transaction attempt (and the very
next task run). There is no polling interval that could let one more payment
through in the gap.

> [!IMPORTANT]
> These controls change the "Agent active" check, which is check **#2** in the
> engine — it runs on every evaluated payment regardless of amount, category, or
> approval status. Suspension also blocks new runs before any transaction is
> created.

Related: [Agents](/core/agents) · [How the engine works](/policies/engine) ·
[Human approvals](/policies/approvals).