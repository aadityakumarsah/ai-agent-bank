# LLM keys

Bring-your-own-key credentials under `/api/v1/users/{wallet}/llm-keys`. Keys are
encrypted at rest and never returned.

## `POST /api/v1/users/{wallet}/llm-keys`

```bash
curl -s -X POST localhost:8000/api/v1/users/{wallet}/llm-keys \
  -H 'content-type: application/json' \
  -d '{"provider":"openai","api_key":"sk-…","label":"Work key"}'
```

Providers: `openai` (→ `gpt-4o`), `anthropic` (→ `claude-sonnet-4.0`),
`google` (→ `gemini-2.0-flash`). Calling again for the same provider
**overwrites** the stored key.

## `GET /api/v1/users/{wallet}/llm-keys/status`

Config status for the wallet:

```json
{ "has_key": true, "provider": "openai", "model": "gpt-4o", "label_masked": "***" }
```

> [!IMPORTANT]
> No endpoint returns the key. Decrypted secrets live only in backend memory for
> the duration of their owner's proposal call, then are dropped.

## `GET /api/v1/users/{wallet}/llm-keys`

Metadata list, not key material.

## How the runtime uses them

`agent_runtime` at run time:

1. Checks whether the user has a key for the configured provider (or its
   default).
2. If yes → constructs a real HTTP call to the provider (OpenAI/Anthropic/Google
   client) with your credential, enforcing the two-action JSON contract via the
   system prompt.
3. If no → uses the deterministic mock proposer, so the loop still runs in demos.

A generic anonymized error surfaces when the upstream call fails (`LLM_CALL_
FAILED`); the API never echoes the key, the upstream secret, or a raw request
body.

> [!NOTE]
> Marking provider `"none"` from Settings disables real calls and uses the mock
> proposer — identical pipeline, just deterministic. See
> [Bring your own LLM key](/guides/byo-key).

Next: [Demo endpoints](/api/demo).