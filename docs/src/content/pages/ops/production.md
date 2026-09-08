# Production checklist

Everything to verify before running with real money. This page is the
"go-live" gate: it separates **engineering** steps from the **business/legal**
steps that depend on how you choose to hold customer funds.

## 1. Engineering guardrails (already in the code)

These are enforced by the application itself, not policy. Read
`backend/app/core/config.py` and `backend/app/core/security.py` for the detail.

### Fail-fast configuration
* `ENVIRONMENT=production` turns on a startup validation
  (`settings.verify_production_config()`) that **refuses to boot** when the
  deployment is unsafe: default `SECRET_KEY`, `DEMO_MODE` on, sqlite
  `DATABASE_URL`, real-payment requested without Solana keys, missing
  `LLM_KEY_ENCRYPTION_KEY`, or localhost Redis.
* No silent mock fallback: `USE_REAL_PAYMENT=true` with a misconfigured Solana
  service raises instead of downgrading to MOCK — you can never think you're
  live while actually simulating real money (see `get_payment_service`).

### Wallet-ownership authentication
* `POST /api/v1/auth/nonce` returns a signed challenge message.
* `POST /api/v1/auth/verify` checks an Ed25519 signature over that message and
  issues a JWT (`sub` = wallet address).
* `GET /api/v1/auth/me` returns the wallet behind a Bearer token.
* With `REQUIRE_AUTH=true`, wallet-scoped routes enforce that the authenticated
  wallet matches the wallet in the path (401 without a token, 403 on mismatch).
  Demo mode leaves it off so the mock flow works without a wallet.

### Database
* Production uses managed Postgres via `DATABASE_URL` and Alembic migrations
  (`alembic upgrade head`). Auto `create_all` is disabled in production.
* `/health/live` (liveness) and `/health/ready` (DB reachability) probes for
  orchestrators and uptime monitors.

## 2. Deployment steps (when you're ready)

| # | Step | Where |
|---|------|-------|
| 1 | Managed Postgres (e.g. Render Postgres, Neon, Supabase) | provider dashboard |
| 2 | `DATABASE_URL` → the Postgres connection string | env var |
| 3 | Run `alembic upgrade head` against it | CI / release job |
| 4 | `REDIS_URL` → managed Redis | env var |
| 5 | `SECRET_KEY` → strong random value, rotated under lock | env var |
| 6 | `LLM_KEY_ENCRYPTION_KEY` → Fernet key (32 bytes, urlsafe b64), **not** derived | env var |
| 7 | `ENVIRONMENT=production`, `DEMO_MODE=false`, `REQUIRE_AUTH=true` | env vars |
| 8 | Solana keys scoped to devnet → confirm flows → then mainnet | env vars, only after legal review |
| 9 | Custom domain + TLS; wire `/health/ready` to uptime monitor | hosting / monitoring |

## 3. Business & legal (the custody decision)

Real customer money is not a code problem — it is a licensed financial
activity. Choose a custody path and integrate accordingly:

### Option A — Regulated partner (recommended to pursue)
You do not self-custody customer funds; a licensed provider holds them.
* **Stripe / Circle / Coinbase Commerce** style providers handle internalisation,
  KYC/AML, and settlement.
* Integration surface: replace the Solana `PaymentService` with a partner-backed
  `PaymentService` (same interface) that creates payment intents, holds balances
  with the partner, and settles to agent escrows on approval. The policy engine,
  idempotency, approvals, and audit trail stay unchanged.
* You still need to comply with your partner's terms and (likely) register as a
  money services business or use their licensed rails.

### Option B — Self-custody (advanced, high regulatory risk)
Users own their keys; the platform holds nothing. Higher legal risk and requires
jurisdiction-specific legal advice before launch.

### Option C — Non-custodial demo forever
Run with MOCK/devnet only. Fully safe to operate, but never moves real money.

## 4. Verify before every go-live

```bash
cd backend
export ENVIRONMENT=production DEMO_MODE=false USE_REAL_PAYMENT=true \
  DATABASE_URL=... SOLANA_RPC_URL=... SOLANA_PRIVATE_KEY=... \
  LLM_KEY_ENCRYPTION_KEY=... REDIS_URL=... SECRET_KEY=...
uvicorn app.main:app
```

The process must **fail to start** if any required secret is missing. Then
smoke-test:
- `GET /health/ready` → `{"status":"ready"}`
- `POST /api/v1/auth/nonce` + `verify` → token
- `GET /api/v1/auth/me` with token → your wallet
- Fund an agent, approve a payment, confirm the on-chain signature on
  devnet before enabling mainnet.