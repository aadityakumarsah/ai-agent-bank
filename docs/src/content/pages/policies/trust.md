# Recipient trust

The policy only knows what the model *claims* a recipient is. It cannot yet
cryptographically prove "human vs agent" from an address, so the engine enforces
conservative, explicit rules about who may receive money.

## The three ways to be trusted

A recipient is trusted when any of these is true:

1. **It is in the policy allowlist** — `allowed_recipient_addresses`, set by the
   human.
2. **It is a known provider** — matches one of the engine's built-in
   `TRUSTED_RECIPIENTS` (demo registry), e.g.: `rpcProvider`, `apiProvider`,
   `dataProvider`, `agentPeer`, `computeProvider`, `storageProvider`,
   `trustedMerchant`.
3. **It is another registered agent** — payments in the `agent` category to a
   peer agent.

The demo provider map mirrors `trust_registry.py`, which also power the
marketplace's demo recipients.

## The gate: `blocked_human_transfers`

If a recipient is **not** whitelisted and **not** a known provider, the engine
checks the policy's `blocked_human_transfers` flag:

- `true` (default) → **blocked**, with *"Recipient 'X' is unknown. Human
  transfers are disabled."*
- `false` → allowed past this check (still subject to every other check).

So by default, an agent can only pay **whitelisted addresses, known providers,
or other agents**. Arbitrary human wallets are refused — this is the main defence
against an agent funneling funds to an attacker's address.

## The marketplace angle

Service listings carry their provider `wallet_address` (demo names like
`apiProvider`). When an agent buys a service, the recipient resolves through the
same trust logic, mapping marketplace categories onto policy categories:

| Service category | Mapped policy category |
|---|---|
| `api` | `api` |
| `compute` | `compute` |
| `data` | `data` |
| `ai_model` | `api` |
| `storage` | `data` |
| `other_agent` | `agent` |

> [!WARNING]
> Allow-listing an arbitrary address is a deliberate escalation of trust. Keep
> `allowed_recipient_addresses` empty unless you are sure about the recipient,
> and keep `blocked_human_transfers` enabled.

Next: [Human approvals](/policies/approvals).