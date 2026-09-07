# Database & migrations

SQLAlchemy 2 declarative models in `backend/app/db/models.py`, migrated by
Alembic. Default backend is SQLite (`backend/bank.db`); set `DATABASE_URL` for
Postgres.

## Core tables

| Table | Contents |
|---|---|
| `users` | wallet users (`wallet_address` unique) |
| `agents` | spending entities: `name`, `description`, `balance`, `total_spent`, `status` (`active/suspended/killed`), `escrow_address`, `revoked` |
| `policies` | one-to-one per agent: caps, categories, block flags, `require_approval_above`, `allowed_recipient_addresses` (JSON) |
| `transactions` | the ledger: `idempotency_key` (unique), `tx_hash`, `status`, `amount Numeric(20,6)`, `category`, `recipient_*`, `rejection_reason`, `risk_score`/`risk_level`, `executed_at` |
| `transaction_logs` | per-transaction diagnostic lines (the engine's check results) |
| `audit_logs` | append-only event account |
| `run_records` | task runs: `task`, `status`, `result`, `steps` (JSON trace) |
| `user_llm_keys` | per-user encrypted credentials: `provider`, `api_key_encrypted` (Fernet), `model`, `label` |
| `marketplace_services` | service directory: `name`, `category`, `endpoint`, `wallet_address`, `price`, `risk_level`, `is_demo` |

## Migration history (Alembic)

| Revision | Title |
|---|---|
| `e70155e7e787` | initial schema |
| `9f2c4b1a3d8a` | service directory |
| `b7f2a4d1c3e9` | transaction idempotency |
| `c8d4b2a5e6f1` | policy monthly limit |
| `d0e5f2a3b8c1` | user llm api keys |

There is also an equivalent set of `sql/*.sql` DDL files in the repo so the
schema is readable without running migrations.

## Apply

```bash
cd backend && alembic upgrade head
```

The app also auto-creates tables on startup when the schema is absent, so a
fresh checkout generally boots and migrates with no manual step. Seeds: the
service directory and demo agents are (re)seeded when `DEMO_MODE` is on (see
[Environment](/ops/env)).

## Concurrency notes

- `idempotency_key` is **unique** — double-submits collide by design.
- Execution-time caps re-read the DB inside the same request as the transfer,
  so concurrent approvals cannot jointly exceed a daily/monthly cap.
- In SQLite dev setups, `transaction_logs`/`audit_logs` grow fast if you hammer
  the demo runner — fine locally, and the Postgres path is used when scaled.

> [!IMPORTANT]
> Withdrawals are blocked by policy, and there is no agent-delete path, so rows
> are additive: *never* hand-edit the ledger to "fix" a demo balance — recreate
> the agent or reset the database instead.

Next: [Environment variables](/ops/env).