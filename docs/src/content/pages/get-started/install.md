# Install & run locally

## Requirements

| Component | Requirement |
|---|---|
| Backend | Python 3.10+ |
| Frontend | Node.js 18+ (npm) |
| Database | none by default — SQLite is used automatically |
| Redis | optional — an in-memory store with identical semantics is used otherwise |

## Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run it:

```bash
uvicorn app.main:app --reload --port 8000
```

### Configuration file

The backend reads its environment from `backend/.env` (a `pydantic-settings`
`env_file`). If the file does not exist the app still boots with safe defaults:
mock payments, SQLite database, demo mode on.

The backend also respects a `.env` at the repo root for convenience — either is
fine; the effective configuration is shown by `GET /api/v1/status`. See
[Environment variables](/ops/env) for every setting.

```bash
# backend/.env
# Leave SOLANA_RPC_URL blank for mock mode (safe default).
SOLANA_RPC_URL=
SOLANA_NETWORK=devnet
USE_REAL_PAYMENT=false
DEMO_MODE=true
```

> [!WARNING]
> `SOLANA_PRIVATE_KEY` is the master key used to derive every agent's escrow
> keys. It must **never** be committed, exposed through the API, or prefixed with
> `NEXT_PUBLIC_`. It is read only by the backend.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The frontend connects to the
backend at `http://localhost:8000`. Override with:

```bash
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Verifying the install

```bash
curl -s localhost:8000/health                 # healthy + version
curl -s localhost:8000/api/v1/status          # effective configuration
curl -s localhost:8000/api/v1/services        # seeded service directory
curl -s -X POST localhost:8000/api/v1/demo/scenarios/success/run \
  -H 'content-type: application/json' -d '{"client_request_id":"demo1"}'
```

## Two ways to run payments

| | Mock mode (default) | Real mode (devnet) |
|---|---|---|
| Env | `SOLANA_RPC_URL` blank | `SOLANA_RPC_URL` + `SOLANA_PRIVATE_KEY` set, `USE_REAL_PAYMENT=true` |
| Hash | `mock_…` | real devnet signature |
| Explorer | no | yes (`explorer.solana.com`) |
| Balance | ledger moves | chain + ledger |

The mode is reported in every payment response as `mode` and `simulated`, and on
the dashboard as the network chip — simulated money is never silent.
[Go live on devnet](/guides/realmode) explains the switch carefully.

Next: [Repository layout](/get-started/repo).