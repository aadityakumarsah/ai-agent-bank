# Security model

AI Agent Bank is built around six guarantees (`SECURITY.md` in the repo). Every
feature traces back to one of them.

## The six guarantees

1. **The AI never touches private keys.** Agents get a derived `escrow_address`;
   the key material stays server-side and is only used to sign exactly the
   transactions the policy engine approved.
2. **No payment without policy.** Every payment — task runs, marketplace, demo
   scenarios — funnels through the same `payment_flow`:
   idempotency → policy engine → balance check → execution.
3. **Humans stay in the loop.** Payments above the approval threshold pause and
   wait. A human can suspend or kill an agent instantly; killed agents cannot
   run tasks or pay.
4. **Everything is auditable.** Every agent action and payment writes an audit
   row and appears in the transaction ledger, in both mock and real mode.
5. **Mock mode always tells the truth.** Simulated payments are labelled
   `mode="mock"`, `simulated=true`, `tx_hash` prefixed `mock_`. No silent
   switch from fake to real money.
6. **Deterministic, transparent policy.** The engine runs the same checks in the
   same order every time and returns each check's pass/fail.

## Reference checks in code

- Nothing signs without `payment_flow.attempt_execution`, which itself only runs
  after `policy_engine.evaluate_transaction` returns `allowed`.
- The AI proposal format is constrained to two JSON actions, and proposal parsing
  is deterministic (`agent_runtime.parse_proposal`).
- Payments that need approval never execute — `mark_approval_required` pauses;
  the workflow explicitly takes the human's decision before any money moves.

## The controls

| Control | Where |
|---|---|
| Rate limiting | per-endpoint limiters (`dependencies/limiter.py`), Redis or in-memory |
| Idempotency | unique `idempotency_key` on every money path |
| Structured logs | JSON + per-request `X-Request-ID`, no secrets, no stack traces in responses |
| `DEMO_MODE` gate | one-click demo endpoints return `403` when off |

> [!IMPORTANT]
> Security boundaries only hold where they are verified by tests. Read
> [Testing](/ops/tests) to see how these guarantees are exercised (policy
> blocks, approvals, idempotency, rate limits, error shapes).

Next: [Threat model](/security/threat).