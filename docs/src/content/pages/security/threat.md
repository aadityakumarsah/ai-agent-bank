# Threat model

A summary of the threats this system is built to absorb — and the specific
control that mitigates each one (`SECURITY.md`).

## The threat table

| Threat | Mitigation |
|---|---|
| Malicious model prompt tries a huge payment | per-tx / daily / monthly caps + category allow-list + approval gating |
| Model exfiltrates to its own wallet | `blocked_human_transfers`, constrained recipient allow-list, registry-based trusted providers |
| Double-payment via retries | idempotency keys on every payment path |
| Abuse of public endpoints | rate limiters + per-request id correlation |
| Secret leaks | key material only in env vars; never stored or returned; escrow derivation |
| End-user LLM keys leaked at rest | encrypted with Fernet (`LLM_KEY_ENCRYPTION_KEY`); never returned by the API; only decrypted in-process for the owner's task run |
| Concurrent approvals sneak past caps | limits re-checked at execution time under the same request as the money movement |
| Demo endpoints transacting a live deployment | `DEMO_MODE` gate: `false\|0\|off\|no` returns 403 from scenario endpoints |

## Reasoning through the more interesting rows

**Model exfiltration.** The engine cannot tell a human wallet from an agent
wallet cryptographically — it enforces structure instead. By default an agent may
only pay whitelisted addresses, known providers, or other agents
([Recipient trust](/policies/trust)). An attacker wallet the model invents is
"unknown" and rejected while `blocked_human_transfers` is on.

**Secrets.** `SOLANA_PRIVATE_KEY` is read only by the backend and never surfaced
through an endpoint. End-user LLM keys are encrypted before storage and never
returned — the API only reports *whether* a key exists
([Private keys](/security/keys)).

**Double-pay.** Idempotency keys are unique on `transactions`. A retry of an
executed flow returns the same transaction (`already_processed: true`), and
approving an already-executed payment is a no-op.

**Honest mock.** There is no configuration in which simulated and real
transactions are indistinguishable. A blank RPC forces mock; real requires an
explicit opt-in (`USE_REAL_PAYMENT=true`).

## What is *not* in scope yet

- **Multi-user authorization.** The API is wallet-scoped by address, not
  authenticated sessions — anyone who knows a wallet address can read its
  agents/transactions via the public API. There is no token auth layer today.
- **On-chain receiver verification.** The trust engine is a registry/allowlist
  model, not an on-chain attestation of "this address is a merchant".
- **Mainnet.** Real-mode is exercised on devnet only.

> [!WARNING]
> Keep this in mind before exposing the backend publicly. The production
> checklist ([Production deployment](/advanced/production)) covers the
> hardening steps that are planned, not yet shipped.

Next: [Audit trail](/security/audit).