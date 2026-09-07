# Environment variables

The backend reads a `.env` in `backend/`; the frontend reads `.env.local`. Where
a value is needed but optional, the code supplies safe defaults — a plain
`pip install && uvicorn` runs in mock mode with SQLite and in-memory rate limits,
zero config.

> [!NOTE]
> The repo intentionally ships **no `.env.example`**: the README's
> `cp .env.example` line is aspirational. Defaults below are what the code
> actually falls back to when a variable is absent.

## Backend (`backend/.env`)

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./bank.db` | primary ledger (Postgres for scale) |
| `DEMO_MODE` | `true` | arms the one-click demo endpoints; `false`/`0`/`off`/`no` → 403 |
| `USE_REAL_PAYMENT` | `false` | opt-in real Solana payments |
| `SOLANA_RPC_URL` | blank | blank forces mock mode |
| `SOLANA_PRIVATE_KEY` | blank | master keypair; derives every escrow (real mode) |
| `SOLANA_USDC_MINT` | devnet USDC | overrides the mint per network |
| `SECRET_KEY` | derived | backend security / fallback key material |
| `LLM_KEY_ENCRYPTION_KEY` | fallback from `SECRET_KEY` | Fernet key (urlsafe base64 of 32 bytes) for user LLM keys |
| `BACKEND_CORS_ORIGINS` | `http://localhost:3000` | CORS allow-list (JSON or comma) |
| `REDIS_RATE_LIMIT_URL` | blank | blank = in-memory rate limits; set for Redis |
| `DEFAULT_LLM_PROVIDER` | `mock` | default model provider for task runs |

Placeholder convention for these docs and for `.env` files: values shown bare
like `sk-`/`4zMM…` mean **substitute your own** — never commit real secrets.

## Frontend (`frontend/.env.local`)

| Variable | Default | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | backend base |
| `NEXT_PUBLIC_SOLANA_NETWORK` | `devnet` | wallet network |
| `NEXT_PUBLIC_SOLANA_RPC_URL` | devnet RPC | wallet RPC for balance/ATA lookups |
| `NEXT_PUBLIC_SOLANA_USDC_MINT` | devnet USDC mint | must match the backend mint |

## Pick your profile

| Profile | `SOLANA_RPC_URL` | `USE_REAL_PAYMENT` | `DEMO_MODE` |
|---|---|---|---|
| Everything mock | (blank) | `false` | `true` |
| Devnet real-ish | a devnet URL | `true` | `false` for clean behaviour |

> [!WARNING]
> `USE_REAL_PAYMENT=true` + blank `SOLANA_RPC_URL` is impossible by design
> (blank forces mock), and `aware` mismatches between frontend and backend mints
> sign tokens the backend won't recognize. Keep
> `NEXT_PUBLIC_SOLANA_USDC_MINT` in lockstep with `SOLANA_USDC_MINT`.

Next: [Observability](/ops/observability).