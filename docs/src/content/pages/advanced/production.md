# Production deployment

This project is a demo-grade architecture with a deliberately honest boundary:
the **documented guarantees** are real, and the **hardening** for public
deployment is largely planned, not shipped. This page is that boundary.

## What is production-ready today

- The money path (policy → balance → execution) and its idempotency.
- Structured logging + `X-Request-ID` correlation.
- Rate limiting (Redis-backed when configured).
- Encrypted-at-rest user LLM keys.
- The `DEMO_MODE` gate refusing demo endpoints in production mode.

## The hardening checklist (planned)

| Area | Today | Production target |
|---|---|---|
| Authentication | none — API is wallet-scope by address | per-user auth / API keys |
| HTTPS | dev only | TLS everywhere + trusted proxies for ip-based limits |
| Database | SQLite default | Postgres (`DATABASE_URL`) |
| Rate limiting | Redis opt-in | required |
| Secrets | env vars | a secrets manager (Vault/SSM) |
| Demo mode | env switch | enforced false in deployments (deny-by-default) |
| Receiver verification | registry/allowlist | on-chain attestation of merchant addresses |
| Mainnet | devnet only | after receiver-verification + auth land |

## Deploy checklist (what to actually do)

1. `DEMO_MODE=false` (actually any of `false`, `0`, `off`, `no`) — the demo
   runner and one-click scenarios then refuse with **403**.
2. Keep `USE_REAL_PAYMENT` off unless the RPC, mint, and key are confirmed.
3. Back up `SOLANA_PRIVATE_KEY` **off-band** — losing it orphans every escrow.
4. Point rate limits at Redis; set `DATABASE_URL` to Postgres and run
   `alembic upgrade head` as a deploy step.
5. Decide the model path: either let users set LLM keys (encrypted) or set a
   server default — never run the deterministic mock as the *default* proposer
   for real traffic unless that's intended.
6. Rotate, constrain, and log **everything**; expect `X-Request-ID` in your
   error-report pipeline.

## What to watch in prod

- The absence of auth means **any wallet address is readable** via the API. Ship
  auth in front of the ledger before exposing it publicly.
- `already_processed` idempotency rows accumulating symp ≫ 0 usually means a
  client retry loop — good, but worth a metric.
- Demo-balance drift is normal in demo mode; only honest on-ledger flows are
  worth alerting on.

> [!IMPORTANT]
> Never treat mock labels as production truth: mock and real share the code path,
> and only `mode` / `simulated` on each transaction tell them apart afterwards.

Next: [FAQ](/advanced/faq).