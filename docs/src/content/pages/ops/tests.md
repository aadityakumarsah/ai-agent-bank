# Testing

The backend's test suite (`backend/tests/`) is the proof of the security model —
it usually ends up pointing at the exact invariants documented in
[Security model](/security/security).

## Run

```bash
cd backend
pytest -q            # whole suite
pytest tests/test_policy_engine.py   # one file
```

Tests use the FastAPI `TestClient` with an isolated SQLite session, so they run
fast and are repeatable against a clean ledger.

## What the suite covers

| File | Proves |
|---|---|
| `test_approvals` | human approvals: pause on threshold, approve→executed, reject→rejected, no-op on re-approve, conflicts |
| `test_demo_scenarios` | scenario runner traces, idempotency per `client_request_id`, gate behaviour |
| `test_integration` | user → agent → policy → fund → task → executed payment end-to-end, in mock mode |
| `test_llm_keys` | encrypt-at-rest, never-returned keys, provider/model resolution |
| `test_marketplace` | request/pay/call flow, `payment_required`, blocked vs paid results |
| `test_part10` | the 10-part build regression assertions (spend caps, mode labels) |
| `test_policy_engine` | every check in the engine, limits re-checked, enabled gates, recipient trust |
| `test_rate_limits` | limiters fire (429) without leaking state |
| `test_status_and_errors` | health/status shape + the error codes (`agent_suspended`, `insufficient_balance`, …) |
| `conftest.py` | app + DB fixtures |

These tests are why signals like `mode:"mock"` / `simulated:true` and rejection
reasons are stable — they are asserted, not aspirational.

## Style expectations

- **Focused, but end-to-end where money is involved.** A payment test goes
  through the real `payment_flow` rather than mocking it.
- **No network.** Real Solana/LLM calls are not exercised; mocks stand in for the
  chain and providers.
- Money semantics (`executed` label, idempotency) are asserted in integration
  tests, not just unit tests.

> [!NOTE]
> `main.py`, the root `seed.py` script, and one or two legacy service files
> (`tools.py` etc.) carry pre-existing lint warnings unrelated to the docs work.
> `ruff check` is feasible to run per-file, but a repo-wide zero-warnings state
> is a backlog item, not today's contract.

Related: [Observability & rate limits](/ops/observability) ·
[Threat model](/security/threat).