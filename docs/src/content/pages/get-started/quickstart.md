# Quickstart

Run the full stack locally and watch an agent propose, pass, and execute a
payment — all in mock mode with zero external keys.

## Prerequisites

- Python 3.10+ and Node.js 18+
- Nothing else: no wallet, no API keys, no Solana RPC in mock mode

## 1. Start the backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

On startup the app creates its tables and, because `DEMO_MODE` defaults to **on**,
seeds seven demo services plus a demo wallet with three policy-locked agents
(`ResearchBot`, `ComputeBot`, `DataBot`) and a realistic labelled history.

Check it:

```bash
curl -s localhost:8000/health
# {"status":"healthy","api_version":"0.2.0"}
```

```bash
curl -s localhost:8000/api/v1/status
# {
#   "payment_mode": "mock",
#   "use_real_payment": false,
#   "llm_configured": false,
#   "demo_mode": true,
#   "missing_config": ["SOLANA_RPC_URL", "SOLANA_PRIVATE_KEY", ...]
# }
```

## 2. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The dashboard talks to the
backend at `http://localhost:8000` (override with `NEXT_PUBLIC_API_URL`).

## 3. Make your first payment

The fastest way to see the full journey is the **Marketplace → One-click Demos**
tab, or the same flow over the API:

```bash
curl -s -X POST localhost:8000/api/v1/demo/scenarios/success/run \
  -H 'content-type: application/json' \
  -d '{"client_request_id":"demo1"}'
```

This auto-provisions a deterministic `ResearchBot` with $100 of simulated USDC,
runs the real `agent → bank → policy → USDC → API` path, and returns a
frame-by-frame trace. The outcome:

- `$0.02` purchase of the **Solana RPC API**
- every policy check passes (under the per-tx limit and approval threshold)
- a `mock_…` USDC payment executes and the ledger moves

> [!NOTE]
> Because the flow is keyed by `client_request_id`, re-running the same request
> is **idempotent**: it returns the existing transaction and never double-pays.

## What happened under the hood

Even in mock mode the real pipeline runs:

1. The task proposer (deterministic mock AI) proposes a payment.
2. `policy_engine` evaluates it check-by-check.
3. `payment_flow.attempt_execution` verifies balance, executes the (simulated)
   transfer, and writes the ledger + audit row.

Next: [How it works](/core/how-it-works), or jump to
[Install & run locally](/get-started/install) for environment details.