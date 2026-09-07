# Create and run a task

Tasks are how the human tells the agent what to do. The task string is plain
language; the runtime proposes one structured action and the policy decides.

## Run from the dashboard

1. Open an **agent** (Agents → your agent).
2. In the **Task Runner**, type something like
   *"Test the RPC provider and report cost"*.
3. Hit run. The result trace shows propose → evaluate → decide → execute, with
   the proposal JSON, every policy check, and the transaction.

## Run from the API

```bash
curl -s -X POST localhost:8000/api/v1/users/{wallet}/agents/1/runs \
  -H 'content-type: application/json' -d '{"task":"Pay $2 to the data provider"}'
```

```json
{
  "run_id": 1,
  "status": "completed",
  "blocked": false,
  "result": "Payment executed: $2.00 to DataBabe (data). Tx: mock_…",
  "decision": { "allowed": true, "requires_approval": false, "checks": [ … ] },
  "transaction": { "id": 7, "status": "executed", "amount": 2, "tx_hash": "mock_…" }
}
```

## What you can ask for

The runtime produces one of two actions:

- **`respond`** — just answer a question. No money involved.
- **`payment`** — a proposal with `recipient`, `recipient_name`, `amount`,
  `category`, `description`.

The system prompt tells the model the categories are `api / compute / data /
agent`, to keep amounts necessary, and never to propose human-wallet transfers.
Without a custom key, the runtime uses a **deterministic mock** — proposing a
sensible payment given your task, so demos never depend on latency or an API key.

<details>
<summary>How interpretation works</summary>

`agent_runtime.parse_proposal` normalizes the model output: it tolerates code
fences, strips surrounding prose, and falls back to a `respond` action when it
cannot parse a payment. Baseline make: `Deterministic mock proposal → parse →
policy evaluate → execute`. Every step returns fields you can diff against the
LLM output.
</details>

## Outcomes and what to look at

| Trace shows | Meaning |
|---|---|
| `decision.checks` | every engine check with pass/fail — fight the reason, not the model |
| `result`, `status: "blocked"` | engine refused; zero USDC moved |
| `waiting_for_approval` | paused above the threshold; approve/reject in Approvals or in this task runner |
| `transaction.status: "executed"` | money moved — open the transaction for `mode`/`simulated` |

> [!TIP]
> For reproducible demos, run a task on the **ComputeBot** demo agent and paste
> the trace into docs/tickets — the `checks` array is your audit evidence.

Next: [Approve or reject payments](/guides/approvals).