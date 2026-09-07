# Users

The `User` is the human's wallet as a first-class record. Everything else is
scoped under it.

## `POST /api/v1/users`

Register (idempotent — calling repeatedly with the same wallet returns/refreshes
the same user):

```bash
curl -s -X POST localhost:8000/api/v1/users \
  -H 'content-type: application/json' \
  -d '{"wallet_address":"MyWallet123","display_name":"Main wallet"}'
```

```json
{ "id": 1, "wallet_address": "MyWallet123", "display_name": "Main wallet" }
```

The `wallet_address` is the canonical key used in every route below
(`/users/{wallet}/…`). `display_name` is optional.

## `GET /api/v1/users`

List users.

## `GET /api/v1/users/{wallet}`

The user by wallet address.

## What "wallet" means here

- In mock/demo mode the address is any string (the demo seed uses
  `DemoWallet11111111111111111111111111111111`).
- In real mode it's the connecting Solana wallet's base58 address — the address
  your browser wallet uses to sign funding transfers.
- Routes are scoped by this string, not by an auth token today. See
  [Threat model](/security/threat) for the current authentication posture.

> [!NOTE]
> The frontend registers the wallet automatically on connect. You only need these
> endpoints when scripting or testing programmatically.

Next: [Agents](/api/agents).