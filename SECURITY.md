# Security

## Guarantees

1. **The AI never touches private keys.** Agents get a derived `escrow_address`;
   the key material stays server-side and is only used to sign exactly the
   transactions the policy engine approves.
2. **No payment without policy.** Every payment — from task runs, the
   marketplace, or demo scenarios — goes through the same `payment_flow` path:
   idempotency lookup → policy engine → balance check → execution.
3. **Humans stay in the loop.** Payments above the approval threshold pause and
   wait for the human. A human can suspend or kill an agent instantly; killed
   agents cannot run tasks or pay.
4. **Everything is auditable.** Every agent action and payment writes an audit
   row and appears in the transaction ledger in both mock and real mode.
5. **Mock mode always tells the truth.** Simulated payments are labelled
   `mode="mock"`, `simulated=True`, `tx_hash` prefixed `mock_`. There is no
   silent switch from fake to real money. A blank `SOLANA_RPC_URL` forces mock;
   real mode requires an explicit `USE_REAL_PAYMENT=true`.
6. **Deterministic, transparent policy.** The policy engine evaluates the same
   checks in the same order every run; results (including every check pass/fail)
   are returned to the client so a block is never a black box.

## Controls

- **Rate limiting** — per-endpoint limiters (e.g. demo scenarios 30/min, task
  runs 10/min/agent, marketplace payments 30/min). Distributed via Redis when
  configured; falls back to an in-memory store with identical semantics.
- **Idempotency** — every payment flow key is derived from
  `(agent, service, amount)` or `demo:{scenario}:{client_request_id}`; a repeated
  POST returns the existing transaction instead of paying twice.
- **Structured logging** — JSON logs with a per-request `X-Request-ID`; trace
  context is propagated and cleared per request. No stack traces or secrets are
  logged. Errors return clean `{detail, code, errors}` bodies.
- **DEMO_MODE gate** — the one-click demo scenarios are disabled (`403`) when
  `DEMO_MODE=false|0|off|no`, so a live deployment cannot accidentally transact
  demo money.

## Threat model notes

| Threat | Mitigation |
|---|---|
| Malicious model prompt tries a huge payment | policy per-tx / daily / category + approval gating |
| Model exfiltrates to its own wallet | `blocked_human_transfers`, constrained recipient allow-list, registry-based trusted providers |
| Double-payment via retries | idempotency keys on every payment path |
| Abuse of public endpoints | rate limiters + request-id correlation |
| Secret leaks | key material only in env vars, never stored or returned; escrow derivation |
| End-user LLM API keys leaked at rest | encrypted with Fernet (`LLM_KEY_ENCRYPTION_KEY`), never returned by the API, only decrypted in-process for the owner's task run |

## Production checklist

- Set `DEMO_MODE=false` and remove any `mock_` expectations.
- Set `DATABASE_URL` to managed Postgres; run `alembic upgrade head`.
- Set `REDIS_URL` so rate limits and locks are distributed.
- Rotate developer keys; never commit `.env` (see `.gitignore`).
- Verify real-mode payments on devnet before enabling `USE_REAL_PAYMENT=true`.