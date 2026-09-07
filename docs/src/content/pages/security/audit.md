# Audit trail

Every important event — an agent created or funded, a policy changed, a payment
requested, approved, denied, or executed, an agent paused or revoked — is written
to the **audit log** (`audit_logs` table) through `AuditService`.

## Append-only by design

The API exposes **read and insert only**. There is deliberately no update or
delete path, and nothing in the UI mutates these rows. Deletion would require a
direct database operation.

```json
{
  "user_id": 1,
  "agent_id": 12,
  "event": "transaction_executed",
  "actor": "system",
  "detail": {
    "transaction_id": 8,
    "amount": 0.02,
    "recipient": "Solana RPC Provider",
    "recipient_address": "rpcProvider",
    "tx_hash": "mock_…",
    "mode": "mock",
    "simulated": true
  },
  "created_at": "2026-09-01T10:01:00Z"
}
```

## Events

| Event | Typically emitted |
|---|---|
| `agent_created`, `agent_funded` | agent lifecycle |
| `agent_paused`, `agent_resumed`, `agent_revoked` | human status changes |
| `agent_auto_suspended` | automated control |
| `policy_changed` | policy updates |
| `transaction_requested` | a payment record created |
| `transaction_approved` / `transaction_denied` | human decisions |
| `transaction_executed` / `transaction_rejected` / `transaction_cancelled` | settlement / refusal |

Every executed payment additionally records `detail` with the mode and
`simulated` flag, so the trail itself can never misrepresent mock money as real.

## The ledger, the logs, the trail

Three layers record what happened:

1. **`transactions`** — the authored payment attempt and its current state.
2. **`transaction_logs`** — check-level diagnostics attached to a transaction
   (the engine writes `APPROVED: …` / `BLOCKED: …` rows).
3. **`audit_logs`** — the append-only, event-level account of everything.

## Read it

There is no standalone audit endpoint; audit data is surfaced through the
activity feed and dashboard panels which the backend feeds from these tables.
For programmatic reads, query the tables directly:

```sql
SELECT event, actor, detail, created_at
FROM audit_logs
WHERE agent_id = 12
ORDER BY created_at DESC;
```

> [!NOTE]
> The `/api/v1/demo/check` endpoint and policy evaluation also persist block
> diagnostics into `TransactionLog`, so even rejected attempts are explainable
> afterwards.

Next: [Private keys & secrets](/security/keys).