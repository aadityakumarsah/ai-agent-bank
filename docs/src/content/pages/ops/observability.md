# Observability & rate limits

Structured logging, per-request tracing, and defensive rate limiting are wired in
so a misbehaving demo (or attacker) is diagnosable.

## Structured logging

`app/core/logging.py` installs a JSON formatter that emits **one JSON line per
event** with trace context via contextvars:

```json
{ "ts": "2026-09-01T10:01:00Z", "level": "INFO", "logger": "bank",
  "event": "payment_executed", "request_id": "ab32…", "agent_id": 12,
  "transaction_request_id": 8, "decision": "allowed", "amount": "0.02" }
```

`request_id`, `agent_id`, `transaction_request_id`, and `decision` are attached
where relevant. `app/middleware/request_context.py` assigns a `request_id` per
HTTP request (honouring an inbound `X-Request-ID`), keeps it in contextvars, and
**echoes it back** in the `X-Request-ID` response header — so a dashboard error
can be correlated to logs.

## No secrets in logs

The logging guidance is explicit: keys, private keys, and raw API secrets are
never written. Error text that reaches the client is generic
(`LLM_CALL_FAILED`, provider/payment failures), never the raw upstream body.

## Rate limits

`app/dependencies/limiter.py` applies per-endpoint limits; backend is Redis if
`REDIS_RATE_LIMIT_URL` is set, otherwise in-memory:

```text
service-payment   marketplace payments / purchase      30/min
service-demo      one-call service demos               20/min
demo              scenario runner                      20/min
user              registration                         moderate
```

In-memory limits are per-process (fine locally); Redis gives a shared, accurate
counter across workers. A 429 body explains the limit, and audit logs still
capture the attempt.

## The gates that matter for support

- `GET /api/v1/status` — reports `payment_mode`, `demo_mode`, and the rate-limit
  backend in one call.
- `X-Request-ID` on every response — give it to the support log grep.
- `GET /api/v1/transactions` + `TransactionLog` rows — the full decision
  history for any disputed payment.

> [!TIP]
> To debug "why was this payment blocked?", the answer is in three places, and
> they agree: the transaction's `rejection_reason`/`checks`, its `TransactionLog`
> rows, and the audit event `transaction_rejected`. No need to guess.

Next: [Testing](/ops/tests).