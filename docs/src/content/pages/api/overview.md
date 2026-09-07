# API overview

The API is versioned under `/api/v1`. OpenAPI is live at `/api/v1/openapi.json`
and browsable docs at `/api/v1/docs` (Swagger) and `/api/v1/redoc`.

## Base

```
http://localhost:8000/api/v1
```

The frontend defaults to `http://localhost:8000` (`NEXT_PUBLIC_API_URL`
overrides). CORS origins are set by `BACKEND_CORS_ORIGINS` (defaults include
`http://localhost:3000`).

## Style

- **Wallet-scoped routes.** You operate under `/users/{wallet_address}/…`.
  Registration is idempotent (`POST /users`).
- **Deterministic bodies.** Every payment decision returns the full `checks`
  list, `reason`, and `requires_approval`, so the API documents itself.
- **Explicit mode labels.** Any money-involved object carries `mode` and
  `simulated`.
- **Always an object.** Errors are JSON: `{"detail": …}` plus `code`/`error`
  fields where the domain adds them — see [Errors](/api/errors).

## Routing map

| Group | Prefix | Summary |
|---|---|---|
| system | `/health`, `/status` | health + build/config status |
| users | `/users` | register wallet users |
| agents | `/users/{wallet}/agents` | agents, policy, funding, runs |
| transactions | `/users/{wallet}/transactions` | ledger + human approve/reject |
| agent runs | `/users/{wallet}/agents/{id}/runs` | task loop |
| marketplace | `/services` | directory, request/pay/call, one-call demos |
| llm keys | `/users/{wallet}/llm-keys` | per-user encrypted keys |
| demo | `/demo/*` | synthetic check + scenario runner |

## Model changes

- `Transaction.status` uses `pending`, `approved` (paused at approval), `rejected`,
  `executed`, `failed`. "Approval required" transactions are **`approved`**, not
  `pending` — verify the state machine before writing logic against statuses.
- `Agent.status` uses `active`, `suspended`, `killed` (the API models keep
  `revoked` as a sibling for compatibility).

> [!TIP]
> Use the live Swagger UI (`/api/v1/docs`) for exact schemas; this reference only
> summarizes the endpoints that matter plus the invariants.

Reference pages: [Status](/api/status) · [Users](/api/users) · [Agents](/api/agents) · [Transactions](/api/transactions) · [Runs](/api/runs) · [Services](/api/services) · [LLM keys](/api/llm-keys) · [Demo](/api/demo) · [Errors](/api/errors).