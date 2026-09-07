# Welcome

**AI Agent Bank** is a programmable financial permission layer for AI agents.

A human funds an agent with a controlled amount of USDC and defines, in advance,
exactly what that agent is allowed to spend it on. Every payment an agent wants
to make — whether it comes from a task run, a service purchase on the
marketplace, or a demo scenario — passes through the same deterministic policy
engine **before any money moves**.

## The core deal

- **You keep control.** Agents don't hold private keys and don't approve their
  own payments. A policy decides what is allowed; a human decides what needs
  approval.
- **The AI can't override the bank.** Money movement is a deterministic,
  rule-based decision. The model can *propose*; it can never *spend* outside the
  policy.
- **It is honest about money.** Transactions are either real (Solana-USDC) or
  explicitly labelled simulated (`mode="mock"`, `simulated=true`, `mock_`
  hashes). There is no silent switch from fake to real money.

## Two modes

| Mode | Trigger | What happens |
|---|---|---|
| **Mock (demo)** | `SOLANA_RPC_URL` blank, or `USE_REAL_PAYMENT` unset | Payments are simulated, labelled `mode="mock"`, balances move in the ledger but nothing touches a chain |
| **Real (devnet)** | `SOLANA_RPC_URL` + `SOLANA_PRIVATE_KEY` set and `USE_REAL_PAYMENT=true` | Real SPL USDC transfers are built, signed server-side, and submitted to Solana devnet |

The demo experience runs with **zero external keys**: a deterministic mock AI
responder answers tasks, seven demo services are seeded into the marketplace, and
one-click scenarios script the full payment journey. See the
[Quickstart](/get-started/quickstart) to start it in about five minutes.

## What the docs cover

- **[Core concepts](/core/how-it-works)** — agents, escrow wallets, policies,
  task runs.
- **[Policy engine](/policies/engine)** — the deterministic checks behind every
  decision.
- **[Payments](/payments/overview)** — the single guarded path any payment must
  take.
- **[Security](/security/security)** — guarantees, threat model, audit trail.
- **[Guides](/guides/first-agent)** — step-by-step walkthroughs.
- **[API reference](/api/overview)** — every endpoint, request, and response.

> [!IMPORTANT]
> The one-click demo scenarios are gated by `DEMO_MODE`. On a production
> deployment with `DEMO_MODE=false` they return `403` and can never transact
> demo money. This kill-switch is covered in [Pause, revoke & kill switch](/security/kill).

## The landing page

The story the dashboard tells: *"Give AI money. Don't give it unlimited
control."* Launch the dashboard from
[http://localhost:3000](http://localhost:3000), connect the seeded demo wallet, and
you'll see three demo agents — `ResearchBot`, `ComputeBot`, `DataBot` — each with
policy-locked spending and a labelled history of real simulated transactions.

Next: [Quickstart](/get-started/quickstart).