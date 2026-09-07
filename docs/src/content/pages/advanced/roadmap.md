# Roadmap

The current build is a high-fidelity demo: the money path, policy engine, and
audit trail are real; public deployment and the broader product surface are not.
This page separates what ships today from what is planned.

## Shipped (in this build)

- Guarded, idempotent payment path (mock and devnet-real).
- Deterministic policy engine + risk scoring + recipient allowlists.
- Paused human approvals, kill/pause switch, full audit trail.
- Marketplace (x402-style, explicitly non-wire-compatible demo).
- One-click demo scenarios and a synthetic `/demo/check`.
- Bring-your-own-key LLM providers (encrypted).

## Planned

| Item | Status |
|---|---|
| Auth & multi-user permissions | Not shipped — API is wallet-scope only today |
| On-chain recipient / merchant verification | Planned (threat model assumes registry/allowlist for now) |
| Official SDK | Planned — no published SDK yet; API is the interface |
| Webhooks for approvals / payment events | Planned — no webhook API today |
| Mainnet real-mode | Blocked on receiver-verification + auth |
| Risk-score as a decision input | Extension point; advisory today (see [Risk](/policies/risk)) |
| Agent withdraw / recipient management UX | Planned — no withdrawal endpoint |

## Honest framing for reviewers

- **"Demo" is a feature, not a bug**: mock/real and demo-gate are first-class and
  asserted by tests.
- **The docs never overstate**: features absent here are labelled planned/absent
  (official SDK, webhooks, auth) rather than invented.
- The **confidence graph** for the roadmap is the test suite +
  `OPERATING_DOC` + this page.

> [!TIP]
> If you're reviewing for production-readiness, read
> [Production deployment](/advanced/production) first — it is the explicit list
> of what still needs hardening.

Next: [Contributing](/advanced/contributing).