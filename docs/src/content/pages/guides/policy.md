# Configure an agent policy

A policy is one call, but the right policy takes a minute of thought. This guide
maps the fields to what you actually want the agent to do.

## The good default

```json
{
  "max_per_transaction": 20,
  "max_per_day": 100,
  "max_per_month": 1000,
  "allowed_categories": ["api", "compute", "data"],
  "blocked_human_transfers": true,
  "blocked_withdrawals": true,
  "blocked_arbitrary_contracts": true,
  "require_approval_above": 10
}
```

Practical example: *"an agent that may spend up to $20 per call, $100 a day,
$1,000 a month, on APIs/compute/data, never to human wallets, and needs me to
approve anything over $10."*

## Decisions to make

**What categories?** Categories are the only "positive" power grant:
- `api` — RPC, search, web APIs.
- `compute` — rented compute.
- `data` — market data, datasets.
- `agent` — payments to peer agents.

**What amount caps?** Set `max_per_transaction` to the largest single payment you
expect; `max_per_day`/`max_per_month` to your budget. Leave `max_per_month: null`
for unlimited month.

**What needs approval?** `require_approval_above` inserts a human in the loop for
large payments. `null` disables approval; any number pauses payments above it
until approved. See [Human approvals](/policies/approvals).

**Who can get paid?** The three block flags are safety defaults. To pay an
explicit known counterpart, add its address to `allowed_recipient_addresses`
(this is how a real fund provider becomes payable). See
[Recipient trust](/policies/trust).

## Apply it

```bash
curl -s -X PUT localhost:8000/api/v1/users/{wallet}/agents/1/policy \
  -H 'content-type: application/json' -d '{ …the policy above… }'
```

Every change is audited as `policy_changed`. A policy change takes effect on the
**next** evaluated payment — the engine reads the current policy at decision
time, so an in-flight approval re-evaluates against the updated rules.

## Common misconfigurations

| Mistake | Result |
|---|---|
| No policy | every payment refused: "No policy configured for agent" |
| `allowed_categories: []` | every payment blocked on category check |
| `blocked_human_transfers: false` with empty allowlist | the one check that loosens recipient control — think before unsetting |
| Tiny monthly cap + concurrent payments | caps re-checked at execution; burst blocked at execution time |

> [!TIP]
> The demo bots ship with `20/100/1000`, `50/200/2000`, `100/250/500` policies —
> good reference shapes for API-heavy agents.

Next: [Create and run a task](/guides/task).