# How it works

A payment only happens after a deliberate chain of custody: a human funds an
agent, the agent *proposes* an action, a deterministic engine *decides* whether it
is allowed, and only then does money *move*.

## The lifecycle

1. **Connect.** A human connects a Solana wallet (or uses the built-in simulated
   wallet in the dashboard). The backend records them as a `User`
   (`POST /api/v1/users`).
2. **Create an agent.** An agent is a named, policy-bound spending entity owned
   by a wallet. Each agent gets a derived `escrow_address`.
3. **Fund the agent.** Mock mode credits the ledger. Real mode produces a
   reviewable USDC payment request that you sign from your wallet to the agent's
   escrow.
4. **Set a policy.** Per agent you configure limits, allowed categories,
   recipient rules, and an approval threshold. A freshly created agent **cannot
   pay anything** until it has a policy.
5. **Give the agent a task.** The task loop proposes an action.
6. **The policy engine decides.** Every proposal is evaluated check-by-check
   (limits, categories, recipients, approvals). The result — including every
   check pass/fail — is returned to the client.
7. **A human approves (if needed).** Payments above the approval threshold pause
   as `approved` and wait for a human to approve or reject. No money moves.
8. **Money moves through the guarded path.** Approved payments re-check limits,
   verify balance, execute the USDC transfer, and write the ledger + audit row.

## The propose-then-pay loop

The agent never signs anything. The runtime asks the LLM (or the deterministic
mock) for a single JSON proposal:

```json
{"action":"payment","recipient":"rpcProvider","recipient_name":"Solana RPC Provider","amount":0.02,"category":"compute","description":"Test the RPC API"}
```

or a plain response:

```json
{"action":"respond","text":"I researched the providers; here are my notes."}
```

Only a `payment` action enters the policy pipeline. The policy engine sees only
the structured fields — amount, recipient, category — and applies deterministic
rules. This is what makes the system auditable: the same inputs always produce
the same decision.

## Every payment takes the same path

Whether the proposal comes from a task run, a marketplace purchase, or a demo
scenario, it flows through `payment_flow`:

```
proposal → idempotency lookup → policy engine → (approval gate) →
balance check → execution guard (limits re-checked) → USDC transfer →
ledger + audit
```

That is the invariant described in [Payments overview](/payments/overview).

## Mock vs real, always labelled

- **Mock mode** runs the identical pipeline but the transfer is simulated and
  returned as `mode="mock"`, `simulated=true`, with a `mock_` tx hash.
- **Real mode** builds, signs, and submits a real SPL USDC transfer on devnet.

There is no state in between. A blank `SOLANA_RPC_URL` forces mock; real mode
requires an explicit `USE_REAL_PAYMENT=true`.

See the components: [Agents](/core/agents), [Policies](/core/policies),
[Task runs](/core/tasks).

Next: [Agents](/core/agents).