# Policies

A policy is the contract that says what an agent may do with its money. There is
exactly one per agent, and no payment is possible without one.

## The fields

| Field | Type | Default | Meaning |
|---|---|---|---|
| `max_per_transaction` | number | — (required) | Hard cap per single payment |
| `max_per_day` | number | — (required) | Cap over the trailing 24h |
| `max_per_month` | number \| null | `null` | Cap over a rolling 30-day window; `null` = unlimited |
| `allowed_categories` | string[] | `[]` | Categories the agent may spend in: `api`, `compute`, `data`, `agent` |
| `blocked_human_transfers` | bool | `true` | Block payments to unknown/human wallets |
| `blocked_withdrawals` | bool | `true` | Block agents moving funds out of escrow |
| `blocked_arbitrary_contracts` | bool | `true` | Block arbitrary contract interactions |
| `require_approval_above` | number \| null | `null` | Humans must approve payments above this |
| `allowed_recipient_addresses` | string[] | `[]` | Explicit recipient allowlist |

## Permissions model

In the dashboard, the policy editor presents these as **permissions**:

| Permission | Maps to | Notes |
|---|---|---|
| API payments | `allowed_categories` contains `api` | RPC, search, infra APIs |
| Compute | contains `compute` | rented compute |
| Data | contains `data` | market data, datasets |
| Agent payments | contains `agent` | pay trusted peer agents |
| Trading | — | *declared* category; not currently executed by the runtime |
| Human transfers | `blocked_human_transfers` | on by default |
| Withdrawals | `blocked_withdrawals` | on by default |
| Contract interactions | `blocked_arbitrary_contracts` | on by default |

Toggling a category just adds or removes it from the allow-list. The three block
flags are hard gates — the engine refuses rather than asks.

## Safest defaults

A fresh agent has no policy at all (nothing can pay). The demo bots and the
scenario runner configure policies that:

1. keep human transfers, withdrawals, and contracts blocked;
2. allow `api`, `compute`, `data`, `agent` categories;
3. set a per-tx cap, a daily cap, a monthly cap, and an approval threshold.

## What a policy is *not*

- It is **not** a free-form script. There is no code-level custom policy; you
  configure fields, not functions.
- It is **not** enforced by the LLM. The engine is a deterministic rule-evaluator
  (`backend/app/services/policy_engine.py`). Read
  [How the engine works](/policies/engine) for the exact check order.

Next: [Tasks & task runs](/core/tasks), or dive into the
[Policy engine](/policies/engine).