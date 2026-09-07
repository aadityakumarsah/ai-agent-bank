# Tasks & task runs

A **task** is a free-text instruction a human gives an agent, e.g. *"Find the
best Solana RPC provider and test their API."* The runtime turns it into an
execution trace with a deterministic proposal stage.

## The task loop

`POST /api/v1/users/{wallet}/agents/{agent_id}/runs` with `{"task": "..."}` starts
a run. `agent_runtime.execute_task` then walks five stages, recording each one
into the run's `steps`:

1. **Propose** — ask the LLM (or the deterministic mock) for a single JSON
   proposal. End-user keys supplied in Settings override the server key.
2. **Analyse** — parse the proposal, tolerating code fences, prose, and slightly
   malformed JSON. Two actions exist:
   - `{"action":"respond","text":"…"}` → the run completes with that text. No money.
   - `{"action":"payment","recipient":"…","recipient_name":"…","amount":…,
     "category":"api|compute|data|agent","description":"…"}` → continue.
3. **Evaluate** — build a pending `Transaction`, then run the
   [policy engine](/policies/engine) on it.
4. **Decide** — one of three outcomes:
   - **Approval required** → status `waiting_for_approval`, tx becomes
     `approved`, no money moves, the human decides later.
   - **Blocked** → status `rejected` with the engine's reason; zero USDC moved.
   - **Approved** → continue.
5. **Execute** — `payment_flow.attempt_execution` re-checks the balance and the
   daily/monthly caps, signs the transfer, updates the ledger, and fires an audit
   event.

## Run outcomes

| `status` | Meaning |
|---|---|
| `running` | in progress |
| `completed` | responder answered, payment executed, or payment blocked (see `blocked`) |
| `waiting_for_approval` | paused above the approval threshold; human must act |
| `failed` | execution failed (e.g. insufficient balance, provider error) |

A run result looks like:

```json
{
  "run_id": 1,
  "status": "completed",
  "blocked": false,
  "result": "Payment executed: $0.02 to Solana RPC Provider (compute). Tx: mock_…",
  "decision": { "allowed": true, "requires_approval": false, "checks": [ … ] },
  "transaction": { "id": 8, "status": "executed", "amount": 0.02, "tx_hash": "mock_…" }
}
```

## Where the LLM fits (and where it doesn't)

- The LLM proposes; it never signs, never approves, and cannot override the
  engine.
- Proposal parsing and the policy decision are fully deterministic.
- The system prompt constrains the model to the two JSON actions above and tells
  it: *"Only propose amounts you judge necessary. Never propose transfers to
  human wallets."*

> [!WARNING]
> A model in an adversarial prompt could still *attempt* a huge or
> recipient-swapped payment. That is exactly what the policy engine and the
> recipient allow-list are built to refuse — see
> [Threat model](/security/threat).

Next: [How the engine works](/policies/engine).