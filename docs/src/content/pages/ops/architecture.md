# Architecture

The project is two apps plus a shared mental model around a single guarded money
path. `ARCHITECTURE.md` at the repo root is the canonical picture; this page is
the tour.

```
┌──── human (browser wallet) ────┐
│  Next.js dashboard (:3000)     │
└──────────────┬─────────────────┘
               │ NEXT_PUBLIC_API_URL (http://localhost:8000)
┌──────────────▼──────────────────┐
│         FastAPI service (:8000) │
│  app  ┌──────────────────┐      │
│ routers│ (api/api_v1)     │      │
│  │     └──────┬───────────┘      │
│  │      services / policy engine │
│  │         ┌─────────────────┐   │
│  │         │  payment_flow   │   │   ← the ONE money path
│  │         └────────┬────────┘   │
│  │          solana payment svc   │   (mock ⇄ real by env)
│  └───────────┬───────────────────┘
└──────────────┼────────────────────┘
               │          ┌────────────┐
               ▼          ▼            │
          SQLite/Postgres  Redis (opt) │
          (users, agents,  (rate       │
           policies, txs,   limits)    │
           audit, services)            │
               │                       │
               └── Solana devnet RPC ──┘  (real mode)
```

## Backend (`backend/`)

- **FastAPI 0.109 + SQLAlchemy 2** (declarative models), SQLite by default,
  Postgres-capable.
- Routers under `app/api/api_v1`: `users`, `agents`, `transactions`,
  `agent_runs`, `marketplace`, `llm_keys`, `demo`, `demo_scenarios`, `config`.
- Business logic in `app/services`: `payment_flow`, `policy_engine`,
  `risk_engine`, `agent_runtime`, `ai_service`, `payment_service`,
  `audit_service`, `trust_registry`, `secrets`.
- Cross-cutting middleware: request-id context, CORS, structured logging
  (`app/core/logging.py` + `middleware/request_context.py`).

## Frontend (`frontend/`)

- **Next.js 14 App Router** dashboard: `/`, `/dashboard`, `/agents`,
  `/agents/[id]`, `/agents/new`, `/policies`, `/transactions`, `/approvals`,
  `/marketplace`, `/activity`, `/settings`.
- `lib/api.ts` — typed client over `/api/v1`; `lib/types.ts` — shared types.
- Browser wallet helpers (funding transfer building/signing) via Phantom/Backpack
  adapters; reads `NEXT_PUBLIC_SOLANA_*` and `NEXT_PUBLIC_API_URL`.
- Wallet-backed service: solvent/simulation labelling is UI-level; backend is the
  source of truth for mode.

## The one money path

`payment_flow.py` is imported by every money-touching caller (task runs,
marketplace, demo scenarios, approvals). Its module docstring is explicit:

- one path, idempotent, policy-gated, balance-checked, audited, deterministic;
- mock and real share it; the only difference is the `SolanaPaymentService`
  behind the transfer, selected at startup from env.

## Databases

- Primary ledger: SQLite by default (`backend/bank.db`), Postgres optional
  (`DATABASE_URL`). Migrations via Alembic — see [Database](/ops/database).
- Rate limits: in-memory by default, Redis when `REDIS_RATE_LIMIT_URL` is set —
  see [Observability](/ops/observability).

> [!IMPORTANT]
> The docs site, backend, and frontend are three separate processes. The
> dashboard talks to `:8000`, the backend talks to Solana only in real mode, and
> **nothing** bypasses `payment_flow` to move money.

Next: [Database & migrations](/ops/database).