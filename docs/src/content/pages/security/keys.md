# Private keys & secrets

The system has exactly two kinds of secrets: the **master keypair** that derives
every agent escrow, and **end-user LLM API keys** that let each human bring their
own model credentials. Both are handled very differently — and neither is ever
returned by the API.

## The master keypair (`SOLANA_PRIVATE_KEY`)

- Read from the environment at startup by `PaymentService`.
- Every agent's escrow keypair is **derived deterministically** on demand:
  `derive_extended_key(master_key, f"{owner_wallet}:{agent_id}")`.
- The derived key exists in memory only while signing; it is never persisted and
  never serialized out of the backend.
- Public halves are what you see: `Agent.escrow_address` and the funding
  `to_address`.

> [!WARNING]
> If `SOLANA_PRIVATE_KEY` is lost, every agent's escrow (and the ability to
> move its USDC) is **unrecoverable** — derivation is one-way from this seed.

## End-user LLM keys (your own keys)

Created with `POST /api/v1/users/{wallet}/llm-keys`:

```json
{ "provider": "openai", "api_key": "sk-…", "label": "My OpenAI key" }
```

- **Encrypted at rest** with Fernet. `LLM_KEY_ENCRYPTION_KEY` (a urlsafe base64
  of 32 bytes unicode-safe) is used directly; if it's missing, the code derives a
  stable key by sha256-ing `SECRET_KEY` so the feature still works safely.
- **Never returned.** Responses surface only existence and metadata:
  `{"has_key": true, "provider": "openai", "model": "gpt-4o", …}`.
- Only the **owner's** key is used, and only during that owner's own task runs:
  the runtime passes the decrypted key straight to the provider for that single
  proposal call.
- Providers valid: `openai`, `anthropic`, `google` (with model defaults like
  `gpt-4o`, `claude-sonnet-4.0`, `gemini-2.0-flash`).

## Everything else

| Secret | Location |
|---|---|
| `SECRET_KEY` | env (backend security / fallback derivation) |
| `LLM_KEY_ENCRYPTION_KEY` | env; otherwise derived from `SECRET_KEY` |
| Rate-limit / metrics details | env only |
| Browser wallet keys | the owner's own wallet (Phantom/Backpack), never the backend's |

## Rules the rest of the code follows

1. No secret value is logged (including structured logs and error text).
2. No secret value is echoed in error responses — the backend returns detail
   strings, never captured secrets.
3. LLM keys are not returned by `GET`; the frontend only displays whether a key
   is configured.
4. `SOLANA_PRIVATE_KEY` appears in no response model.

> [!TIP]
> For environment file guidance see [Environment variables](/ops/env). The
> documentation never publishes real values.

Next: [Agent kill switch](/security/kill).