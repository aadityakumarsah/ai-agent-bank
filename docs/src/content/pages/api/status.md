# Status & health

Two trivial endpoints tell you the backend is alive and how it is configured.

## `GET /health`

Liveness probe. Returns `{"status":"ok"}` when the API is up. Use it for load
balancers and container healthchecks.

## `GET /api/v1/status`

Reports the runtime build and the effective configuration:

```json
{
  "status": "ok",
  "service": "AI Agent Bank API",
  "version": "0.2.0",
  "config": {
    "mode": "mock",
    "payment_mode": "mock",
    "rpc_url": "https://api.devnet.solana.com",
    "demo_mode": true,
    "rate_limit_backend": "in_memory",
    "rate_limit_backend_url": null
  }
}
```

What each field means:

- `config.payment_mode` — `mock` unless the backend has `USE_REAL_PAYMENT=true`
  and a non-blank `SOLANA_RPC_URL`.
- `config.demo_mode` — mirrors the `DEMO_MODE` gate that arms/denies the
  one-click demo endpoints.
- `config.rate_limit_backend` — `redis` when `REDIS_RATE_LIMIT_URL` is set (with
  the URL echoed), otherwise `in_memory`.

```bash
curl -s localhost:8000/api/v1/status | jq '.config'
```

> [!TIP]
> `status` is the same data the dashboard's status chip reads — if the chip says
> "Demo mode", the backend config ate `DEMO_MODE=false`.

Related: [Environment variables](/ops/env).