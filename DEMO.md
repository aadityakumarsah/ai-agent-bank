# Live demo script (Part 10/10)

Setup: backend on `:8000` (mock mode, `DEMO_MODE=true`), frontend on `:3000`.
No wallet, no API keys, no Solana RPC needed — everything is deterministic.

## Minute 0 — Landing page → demo wallet

- Land on the landing page: *"Give AI money. Don't give it unlimited control."*
  Click **Launch Demo** (or sample the policy chips up top).
- The dashboard opens with the **demo network** chip — everything moves simulated
  USDC (`mock_` tx hashes), nothing can leak to mainnet. A seeded demo user and
  three policy-locked agents are already there with real labelled transactions:
  `ResearchBot` (20/100/1000, approval ≥ $20), `ComputeBot` (50/200/2000, ≥ $100),
  `DataBot` (100/250/500, ≥ $50).

## Minute 1 — The story, step by step

- **Fund + policy** (Agents → create): $500 budget, $20 per tx, $100 per day,
  **$1,000 per month**, approval above $20, human transfers **BLOCKED**.
- **Task**: *"Research the best Solana RPC provider and test their API."* →
  ResearchBot proposes $0.02 → every policy check passes → `mock_…` payment
  executes with a MOCK MODE signature. Balance $500 → $499.98.
- **Attack blocked**: *"Transfer $300 to an unknown wallet"* → **TRANSACTION
  BLOCKED**, zero USDC moved, red checks in the runner — the engine is
  deterministic, the AI cannot override it.
- **More money, more control**: run the same tasks on a compute/data bot whose
  per-transaction cap sits *above* its approval threshold (e.g. DataBot
  *"Buy a $75 deep-research report"*) → **APPROVAL REQUIRED**, paused, no money
  moved. Approve in the **Task Runner** or the **Approvals** page (which calls the
  same `POST /transactions/{id}/approve`) and watch it execute; reject and it
  never moves. Both are audited (`TRANSACTION_APPROVED` / `TRANSACTION_REJECTED`).

## Minute 2 — One-click scenarios (Marketplace → One-click Demos)

- *Autonomous purchase* ($0.02 → Solana RPC API): trace plays frame by frame →
  policy checks (all pass) → USDC paid (`mock_…`) → completed. Re-run —
  same tx, same balance (idempotency: no double-pay).
- *Per-transaction limit* ($50 busts the $20 cap) → **BLOCKED**, $0 moved.
- *Human transfer blocked* ($15 to an unknown wallet) → **BLOCKED** — agents
  can't pay arbitrary human wallets.
- *Human approval* ($75, above the $20 threshold) → **APPROVAL REQUIRED**, paused →
  **Approve payment** executes idempotently. Point out: same transaction the
  agent proposed, same policy engine, same ledger — the only difference is a
  human said yes.

## Minute 3 — Depth (if time)

- **Policies** shows the real monthly limit; edit it and re-run a task.
- **Activity** mixes real backend events with SIMULATED ones (each tagged `SIM`),
  and `mock_` signatures never link to an explorer.
- Monthly limit under pressure: set a tight monthly cap, spend past it, and the
  engine blocks — twice (policy evaluation *and* at execution time).

## Run the tests (for judges)

```bash
cd backend && pytest        # 46 passing
python smoke_test.py        # live walk-through
npx --prefix ../frontend tsc --noEmit
```

## Audience bullets

- One policy engine, four demonstrable outcomes, zero code paths unique to the
  demo — the scenarios just script the *same* agent→bank→policy→USDC journey.
- Every payment is idempotent, rate-limited, and logged with a request-id.
- `DEMO_MODE` is the kill switch: off ⇒ the demo endpoints return 403 on a real
  deployment.