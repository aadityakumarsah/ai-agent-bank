# Spending limits

An agent's policy defines three stacked caps. Every one of them is evaluated by
the engine, and the daily and monthly caps are additionally **re-checked at the
moment of execution**.

## The three caps

| Cap | Window | Set with |
|---|---|---|
| Per-transaction | single payment | `max_per_transaction` |
| Daily | trailing 24 hours | `max_per_day` |
| Monthly | trailing 30 days (rolling) | `max_per_month` (`null` = unlimited) |

Sums count **executed** transactions only, so a payment waiting for approval or a
blocked attempt does not consume budget.

## Why caps are enforced twice

The policy engine evaluates a payment when it is *requested*. In a burst of
concurrent approvals, each payment could pass its own check — and together they
could push the agent past the daily or monthly cap.

To close that window, `payment_flow.recheck_limits_at_execution` re-runs the
daily and monthly sums under the same request that moves the money. If a cap
would be exceeded, execution is refused and the payment is marked `failed` with a
clear reason.

```
request time:    engine checks daily + monthly                    → approved
execution time:  recheck_limits_at_execution re-verifies both      → executes
```

> [!TIP]
> You can see this in action by setting a tight monthly cap, spending past it,
> and watching the engine block twice — once at evaluation, once at execution.

## What happens when a cap is hit

- **At evaluation** the transaction is `rejected`, zero USDC moves, and the
  rejection reason names the limit and the exact numbers involved
  (`SPENT X; requested Y; allowed Z`). The audit trail records no money change.
- **At execution** the transaction is marked `failed` with
  *"…limit exceeded at execution time"*.

Both are audited, so the trail always explains the decision.

## Example

A `ResearchBot` policy of `20 / 100 / 1000` (per-tx / day / month) with approval
above $20:

- a $0.02 RPC purchase → passes everything → auto-executes;
- a $50 data purchase → **breaks** the $20 per-tx cap → blocked, $0 moved;
- a $75 report → within caps but above the $20 approval threshold → paused.

Next: [Recipient trust](/policies/trust).