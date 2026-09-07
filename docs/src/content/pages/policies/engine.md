# How the engine works

The policy engine (`backend/app/services/policy_engine.py`) is an ordered,
deterministic evaluator. It never consults an LLM. Given a proposed payment it
runs the checks below in a fixed order and returns a decision plus the pass/fail
of every check that ran.

## The output shape

Every decision is returned to the client for transparency:

```json
{
  "allowed": false,
  "requires_approval": false,
  "reason": "Transaction exceeds per-transaction limit. Requested $50 but allowed $20.",
  "checks": [
    { "name": "Agent active", "passed": true, "detail": "active" },
    { "name": "Per-transaction limit", "passed": false, "requested": "50", "allowed": "20" }
  ]
}
```

## Check order

| # | Check | Fails when |
|---|---|---|
| 1 | **Policy configured** | the agent has no policy at all |
| 2 | **Agent active** | agent is `suspended` or `killed` |
| 3 | **Valid amount** | amount ≤ 0 |
| 4 | **Per-transaction limit** | amount > `max_per_transaction` |
| 5 | **Daily limit** | today's executed spend + this amount > `max_per_day` (rolling 24h) |
| 6 | **Monthly limit** | last-30-days spend + this amount > `max_per_month` (rolling 30d; unset = unlimited) |
| 7 | **Category allowed** | category not in `allowed_categories` |
| 8 | **Recipient trusted** | recipient is not whitelisted / not a known provider **and** human transfers are blocked |
| 9 | **Human approval threshold** | amount > `require_approval_above` → returns `requires_approval=true` (`allowed=false`) |

The engine returns at the **first** failing check, which is why a transaction
usually shows a short, precise reason. Approval (check 9) is special: it sets
`requires_approval=true` and returns a decision the API treats as "pause for the
human", not "blocked".

## Determinism & transparency

- Same inputs → same decision, every time.
- Balances and windows are computed from **executed** transactions only
  (`status == executed`) — approvals waiting or blocked attempts never count
  against a limit.
- Every decision is recorded on the transaction as a `TransactionLog`
  (`info`/`error`) and returned to the client.

## Trusted recipients (demo registry)

A recipient is trusted when it is in the policy's explicit
`allowed_recipient_addresses`, matches a known provider in the engine's
`TRUSTED_RECIPIENTS`, or is another registered agent category. The built-in demo
names are `rpcProvider`, `apiProvider`, `dataProvider`, `agentPeer`,
`computeProvider`, `storageProvider`, `trustedMerchant`. See
[Recipient trust](/policies/trust) for the full logic.

> [!IMPORTANT]
> Spend-window sums deliberately **exclude** the transaction being evaluated, and
> the same caps are **re-checked at execution time** so a concurrent batch of
> approvals can never exceed them together. See [Spending limits](/policies/limits).

Next: [Spending limits](/policies/limits).