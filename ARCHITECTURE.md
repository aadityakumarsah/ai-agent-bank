# AI Agent Bank Architecture

## Overview
AI Agent Bank is a programmable financial permission layer that lets humans fund
AI agents with controlled amounts of USDC and define exactly what the agent is
allowed to spend it on. Every agent payment passes a deterministic policy engine
before any money moves.

- Frontend: Next.js dashboard for user interaction
- Backend: FastAPI server handling business logic, policy enforcement, and agent management
- Blockchain: Solana USDC (mock mode by default)
- Database: SQLite for dev / PostgreSQL for production
- Redis: distributed rate limiting + temporary state (with in-memory fallback)

## Core Components

### 1. Frontend (Next.js)
- Wallet connection (Solana wallet adapter) + simulated wallet
- Agent creation/funding, policy editor, transaction history, approvals UI
- Service marketplace with frame-by-frame execution traces and one-click demos

### 2. Backend (FastAPI)
- `app/api/api_v1/` — routers: users, agents, policies, transactions, agent runs,
  marketplace/services, demo scenarios, config/status
- `app/services/payment_flow.py` — the single guarded payment path used by task
  runs, the marketplace, and demo scenarios: idempotency lookup → policy engine →
  balance check → execution
- `app/services/demo_scenarios.py` — deterministic one-click scenarios
  (ResearchBot agent + $100 + scenario policy) gated by `DEMO_MODE`
- `app/services/policy_engine.py` — deterministic evaluation of every payment
- `app/services/payment_service.py` — mock / Solana-USDC implementations
- `app/services/audit_service.py` — append-only audit trail for every action
- `app/api/dependencies/limiter.py` + `app/services/redis_service.py` — rate
  limiting (Redis or in-memory TTL fallback)
- `app/core/logging.py` + `app/middleware/request_context.py` — structured JSON
  logs correlated by `X-Request-ID`
- `app/api/errors.py` + `app/services/errors.py` — domain-coded, clean error bodies
- `app/db/` — SQLAlchemy models; Alembic migrations for schema evolution

### 3. Policy Engine
- Deterministic, ordered checks: per-transaction limit, daily budget, category
  allow-list, recipient trust, approval threshold, agent status, human-transfer
  and withdrawal blocks
- Outputs: `allowed` / `requires_approval` / blocked with a reason and every
  check's pass/fail (returned to the client for transparency)

### 4. Payment Service
- Mock mode: `SOLANA_RPC_URL` blank → simulated txs labelled `mode="mock"`,
  `simulated=true`, `mock_` hashes — never silently real
- Real mode: devnet Solana USDC transfers signed server-side
- Same interface either way; proofs (tx hash, explorer URL) returned uniformly

### 5. Agent Runtime
- Executes AI tasks via LLM providers (deterministic mock when keys are absent)
- Proposes payments through the same `payment_flow` as everything else
- Never holds or exposes private keys; agents have a derived `escrow_address`
- Per-user LLM keys (Settings): encrypted at rest per wallet, preferred over the
  server `.env` key, and used only while the task's proposal is generated

### 6. Data Layer
- Users, Agents, Policies, Transactions (with `idempotency_key`), AuditLog,
  ServiceDirectory demo services, `UserAPIKey` (encrypted, per provider/wallet)
- Alembic migrations (`backend/alembic/`); `init_db()` seeds demo data for dev

### 7. Observability & Reliability (Part 9/10)
- Structured JSON logging with per-request trace context
- Idempotency on every payment path (double-clicks never double-pay)
- Rate limiters per endpoint class (scenarios 30/min, task runs 10/min/agent, …)
- Friendly, code-carrying error responses; no stack traces or secrets in responses
- `DEMO_MODE` gate around the one-click demo endpoints

### 8. Final polish (Part 10/10)
- Monthly spending cap per agent (rolling 30-day window), enforced at policy
  evaluation and re-checked at execution time so concurrent approvals can't slip
  past the cap
- Human approval is end-to-end real: `run_task` pauses above a threshold, and
  approve/reject mutations execute or block through the same guarded payment path
- Seeded demo user with policy-locked agents (ResearchBot / ComputeBot / DataBot)
  and labelled mock transactions so the UI is rich on first boot
- Landing page at `/` with the story dashboard at `/dashboard`

## Security Principles
1. AI never controls private keys
2. Every transaction passes through the policy engine
3. Human remains ultimate authority (approvals, kill/revoke are instant)
4. All financial actions are auditable
5. Policy enforcement is deterministic and transparent
6. Mock mode is explicitly labelled; real mode requires explicit opt-in
7. Secrets live only in environment variables, never returned or logged

## Communication Flow
1. User connects (or simulates) a wallet in the frontend
2. Frontend creates an agent via the backend API
3. User funds the agent (mock: simulated; real: USDC to agent's escrow address)
4. User configures policies → backend persists per-agent policy
5. Agent gets a task (single run) and proposes payments via the backend
6. Policy engine evaluates; approval-gated payments pause for a human
7. Approved payments execute through the payment service; results return to agent
8. Every step logs to the audit trail + transaction ledger

## Development Setup
- Backend: `uvicorn app.main:app --reload --port 8000` in `backend/`
- Frontend: `npm run dev` in `frontend/` (port 3000)
- DB: SQLite default; Alembic for migrations; PostgreSQL for production
- Redis: optional (`REDIS_URL`); in-memory fallback otherwise

## Testing
- `pytest` in `backend/` — 37 tests (scenarios, policy engine, approvals,
  idempotency, rate limits, integration, error shapes)
- `smoke_test.py` — live API walk-through
- Frontend: `npx tsc --noEmit`, `npm run build`

## Deployment Considerations
- `DEMO_MODE=false` for production; demo endpoints then return 403
- Managed Postgres + `alembic upgrade head`
- Redis for distributed rate limiting
- Rotate keys; never commit `.env` (see `.gitignore`)