# Errors & error handling

Every error is returned as JSON, and the app's HTTP client (`api.ts`) surfaces a
consistent `Error` with `detail`, `status`, and context.

## The shape

```json
{ "detail": "…human reason…" }
```

Domain errors add `code` and `error`:

```json
{
  "detail": "Agent is suspended, cannot run tasks or make payments",
  "code": "agent_suspended",
  "error": "agent_suspended"
}
```

## Domain error codes

| HTTP | Code | When |
|---|---|---|
| `400` | `insufficient_balance` | execution refused — amount exceeds the agent balance |
| `400` | `invalid_amount` | amount ≤ 0 |
| `403` | `agent_suspended` | actions on/payments by a suspended agent |
| `403` | `agent_revoked` | actions on/payments by a killed agent |
| `404` | — | unknown user / agent / transaction / service |
| `409` | — | state conflicts (e.g. approving a rejected/failed transaction) |
| `429` | — | rate limit exceeded |
| `500` | — | unexpected failure (anonymized; request-id in logs) |

## Consistency rules the API follows

1. **Detail always quoted from the engine.** Policy refusals return the exact
   decision `reason` string (e.g. *"Transaction above $20 requires human
   approval."*).
2. **No secrets in error text.** Upstream LLM/payment failures map to generic
   messages (`LLM_CALL_FAILED`, provider errors) and never echo keys or request
   bodies.
3. **Idempotent by construction.** A retried double-submit returns
   `already_processed: true` with the existing transaction, not an error.
4. **Rate limiters** (`limits` backend: Redis if `REDIS_RATE_LIMIT_URL`, else
   in-memory) apply to money-adjacent and demo endpoints; 429 bodies explain the
   limit.

## Client behaviour (frontend)

- `request()` throws `Error(message)` where `message` prefers `data.detail`,
  falling back to `data.message`/status text.
- `204` responses (successful no-content mutations) return `undefined`.
- Non-2xx throws, so dashboards can render the engine's reason verbatim.

> [!TIP]
> For automation: check `error.status === 403 && error.code === 'agent_suspended'`
> before deciding whether to retry — the answer is usually "resume the agent",
> not "retry the payment".

Related: [Status](/api/status) · [Threat model](/security/threat).