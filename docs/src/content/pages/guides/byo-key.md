# Bring your own LLM key

By default the runtime uses a deterministic mock proposer, so the whole loop runs
without any API key. To drive **real** model calls, configure your own key per
provider. Keys are stored **encrypted** and never returned by the API.

## Add a key

In the dashboard go to **Settings → LLM Key** and pick a provider:

```bash
curl -s -X POST localhost:8000/api/v1/users/{wallet}/llm-keys \
  -H 'content-type: application/json' \
  -d '{"provider":"openai","api_key":"sk-…","label":"Work key"}'
```

Supported providers and default models:

| Provider | Default model |
|---|---|
| `openai` | `gpt-4o` |
| `anthropic` | `claude-sonnet-4.0` |
| `google` | `gemini-2.0-flash` |

## Check what's configured

**There is no read path that returns the key.** `GET` only answers
existence/metadata:

```json
{ "has_key": true, "provider": "openai", "model": "gpt-4o", "label_masked": "***" }
```

## How your key is used

- Only your **own** keys apply — the runtime binds your task-run proposal to your
  stored credential.
- The decrypted key lives only for the duration of the proposal call, server-side.
- The raw call still must produce the two allowed JSON actions; your key **does
  not** change the policy, the checks, or the payment path.

## Rotate or revoke

`POST /api/v1/users/{wallet}/llm-keys` with the same provider **overwrites** the
record. Keep backups of old keys somewhere safe; once replaced there is no
recovery path.

> [!WARNING]
> Your provider key billing you oversees: the model still can only
> **propose** payments — but it can propose a lot of them. Caps and approvals
> cap spend, latency and cost are not otherwise bounded. See
> [Threat model](/security/threat) for the full attack surface.

Next: [Run the one-click demos](/guides/scenarios).