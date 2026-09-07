# FAQ

### Is the AI actually paying for things in real money?

Only in **real mode** (`USE_REAL_PAYMENT=true` + `SOLANA_RPC_URL`), and only on
devnet. Otherwise every `$` is a simulated ledger unit, explicitly labelled
`mode:"mock"` / `simulated:true`. The *code path* is identical either way.

### Does the agent use my wallet or its own?

Neither directly. Payments are signed by a **server-side derived escrow** for the
agent. Your wallet funds that escrow (a reviewable USDC request in real mode);
the agent can only spend within policy. See [Agent wallets](/core/wallets).

### Why did my payment show "approved" but no money moved?

`approved` here means **paused awaiting a human**, not settled. The policy's
`require_approval_above` threshold was exceeded; approve or reject it from the
Approvals page. Money moves only at `executed`. See
[Human approvals](/policies/approvals).

### My task got blocked. What went wrong?

Open the run trace: `decision.checks` names the exact failing check and reason
(limit, category, recipient, agent). The engine is deterministic — the same
payment always gives the same decision. Fix the policy or the recipient and retry.

### Can I see the audit trail?

There's no standalone audit endpoint; audit events surface via the dashboard's
activity feed, and all rows live in `audit_logs` (append-only, choose your own
DELETE to bypass). Transactions + `TransactionLog` rows re-derive the decision.
See [Audit trail](/security/audit).

### Is this wire-compatible with x402?

No. The marketplace flow is a simplified, self-labelled demo that mirrors the
*shape* of x402 — every response carries an `x402_note` saying it is not
wire-compatible. See [x402 integration](/payments/x402).

### Can I use my own OpenAI/Anthropic/Google key?

Yes — Settings → LLM Key, or `POST /llm-keys`. Keys are encrypted
(Fernet) at rest and never returned by the API; only your own key is used, and
only during your own task runs. See [Bring your own key](/guides/byo-key).

### Why are my "real" transactions still showing `mock_` hashes?

That means the backend is in mock mode: blank `SOLANA_RPC_URL` forces mock, and
`USE_REAL_PAYMENT` must be explicitly `true`. The label is the truth — there is
no hidden half-way state. See [Go live on devnet](/guides/realmode).

### Can an agent move money out of the bank?

Only along the single `payment_flow` path, gated by policy, and never to
arbitrary wallets while `blocked_human_transfers` is on. There is no withdrawal
endpoint. See [Threat model](/security/threat).

### Is there a mobile app or an official SDK?

No. The dashboard is the web app, and there is no published SDK today — the API
is the integration surface. Status for both is **planned**, not live.

Next: [Roadmap](/advanced/roadmap).