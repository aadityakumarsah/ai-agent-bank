# AI Agent Bank

A programmable **financial permission layer** for AI agents. Humans fund agents
with USDC and define exactly what each agent is allowed to pay for. Every agent
payment passes a deterministic policy engine before any money moves.

Built for a hackathon in 10 parts — the current build is **Part 10/10** (final
polish: landing page, seeded demo data, monthly spending limits with an
execution-time re-check, and a human approval flow wired end-to-end).

## Repo layout

- `backend/` — FastAPI service: policy engine, payment service (mock + Solana USDC),
  agent runtime, transaction ledger, audit trail, demo scenarios.
- `frontend/` — Next.js dashboard: agents, policies, transactions, approvals,
  service marketplace with execution traces.

## Quick start

### Backend

```bash
cd backend
cp ../.env.example .env
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Everything runs in **mock mode** by default — AI keys can be blank (deterministic
mock responder) and `SOLANA_RPC_URL` blank means payments are simulated. On
startup the DB is created, 7 demo services are seeded, and a demo user with three
policy-locked agents (`ResearchBot`, `ComputeBot`, `DataBot`) is provisioned so
the dashboard is instantly rich with real labelled transactions.

Play with the one-click scenarios (`DEMO_MODE` defaults to **on**):

```bash
curl -s localhost:8000/api/v1/status
curl -s -X POST localhost:8000/api/v1/demo/scenarios/success/run -H 'content-type: application/json' -d '{"client_request_id":"demo1"}'
```

### Frontend

```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

The dashboard connects to `http://localhost:8000` (override with
`NEXT_PUBLIC_API_URL`).

## One-click demo scenarios

Each button on the **Marketplace → One-click Demos** tab provisions a
deterministic `ResearchBot` (auto-created user, $100 of mock USDC, scenario policy)
and runs the real agent → bank → policy → USDC path, returning a frame-by-frame
execution trace:

| Scenario | What it shows | Outcome |
|---|---|---|
| `success` | $0.02 API purchase, under all limits | auto-approved, paid |
| `blocked-spend` | $50 purchase busts the $20 per-tx cap | blocked, $0 moved |
| `blocked-transfer` | $15 to an unknown human wallet | blocked, $0 moved |
| `approval` | $75 purchase above the approval threshold | paused → human approves → paid |

Idempotent per `client_request_id`: double-clicks never double-pay.

## Human approval (end-to-end)

The approval decision isn't simulated in the UI. `run_task` pauses above a
threshold (status `waiting_for_approval`, no money moved); the Approvals page and
the agent's Task Runner both call `POST /transactions/{id}/approve` (executes
through the same guarded payment path) or `POST /transactions/{id}/reject`
(marks rejected, audited). Try it with an agent whose per-transaction cap sits
above its approval threshold (seeded `ComputeBot` $150 above $100, or `DataBot`
$75 above $50), or the one-click *Human approval* scenario.

## Spending limits

Policies carry per-transaction, daily, and **monthly** caps. The monthly cap is a
rolling 30-day window and is enforced twice: at policy evaluation and again at
the moment of execution (`recheck_limits_at_execution`), so a concurrent batch of
approved payments can never slip past the cap.

## Bring your own LLM key

End users can attach their own OpenAI / Anthropic / Google API key from
**Settings → AI providers** (Settings page). Keys are scoped to the connected
wallet, encrypted at rest with Fernet (`LLM_KEY_ENCRYPTION_KEY`, or auto-derived
from `SECRET_KEY`), never returned raw, and only presented to the matching
provider during a task run. Resolution order for a task: **user's key → server
`.env` key → deterministic mock**. With no keys at all the mock responder keeps
the demo running offline.

## Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest                 # 51 tests: scenarios, policy, approvals, limits, llm-keys, integration
python smoke_test.py   # live API walk-through against a running backend
```

## Real mode (Solana devnet USDC)

Set `SOLANA_RPC_URL`, `SOLANA_PRIVATE_KEY`, `USE_REAL_PAYMENT=true`, optional
`OPENAI_API_KEY`/`ANTHROPIC_API_KEY`/`GOOGLE_AI_API_KEY` in `.env`. The agent's
private key is **never** stored; `escrow_address` is what transactions are funded
and paid from.

## Docs

- [`DEMO.md`](DEMO.md) — what to show during a live demo
- [`SECURITY.md`](SECURITY.md) — threat model and guarantees
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — system overview