# Repository layout

```
bank/
├── backend/            FastAPI service
│   ├── app/
│   │   ├── main.py                 app factory, routers, startup DB init
│   │   ├── api/
│   │   │   ├── api_v1/             users, agents, transactions, runs,
│   │   │   │                       marketplace, llm-keys, demo, scenarios, status
│   │   │   ├── dependencies/       rate limiters
│   │   │   └── errors.py           central exception handlers
│   │   ├── core/                   settings (env), structured logging
│   │   ├── db/                     SQLAlchemy models, session
│   │   ├── middleware/             per-request context (X-Request-ID)
│   │   └── services/
│   │       ├── policy_engine.py    deterministic payment gate
│   │       ├── risk_engine.py      rule-based 0–100 risk scoring
│   │       ├── payment_service.py  mock + Solana USDC implementations
│   │       ├── payment_flow.py     single guarded payment path
│   │       ├── agent_runtime.py    task loop: LLM → proposal → policy → pay
│   │       ├── ai_service.py       OpenAI / Anthropic / Google + mock
│   │       ├── audit_service.py    append-only audit events
│   │       ├── trust_registry.py   known providers (demo)
│   │       ├── secrets.py          Fernet encryption for LLM keys
│   │       ├── redis_service.py    Redis client with in-memory fallback
│   │       ├── seed_demo.py        demo wallet + three agents (demo mode)
│   │       ├── demo_scenarios.py   one-click scenarios
│   │       └── seed_services.py    7 demo marketplace listings
│   ├── alembic/                    migrations
│   ├── tests/                      pytest suite
│   ├── requirements.txt
│   └── requirements-dev.txt
├── frontend/           Next.js dashboard
│   └── src/
│       ├── app/                   pages: dashboard, agents, policies,
│       │                            transactions, approvals, marketplace,
│       │                            activity, settings, landing
│       └── lib/                   api.ts, solana.ts, types.ts, …browser helpers
├── sql/                Generated Postgres/Supabase DDL (compile of the models)
├── docs/               This documentation site
├── .env                Root env mirror (backend reads backend/.env)
├── README.md
├── ARCHITECTURE.md
├── SECURITY.md
└── DEMO.md             Live demo script
```

> [!NOTE]
> The docs site in `docs/` is a self-contained Vite + React app. Run it with
> `cd docs && npm install && npm run dev` (port 3001). It is intentionally
> isolated from the product app.

## Where the important logic lives

- **One guarded money path** — everything funnels through
  `backend/app/services/payment_flow.py`: idempotency lookup → policy engine →
  balance check → execution → ledger + audit.
- **The gate** — `backend/app/services/policy_engine.py` is deterministic and
  LLM-free. `risk_engine.py` adds a transparent rule-based risk score.
- **The agent** — `backend/app/services/agent_runtime.py` runs the *propose then
  pay* loop; `ai_service.py` swaps providers (including the mock responder).
- **Signing** — `backend/app/services/payment_service.py` implements both mock
  and real Solana-USDC forwards; `SOLANA_PRIVATE_KEY` never leaves the backend.

## Docs you can read on GitHub

| File | Covers |
|---|---|
| `ARCHITECTURE.md` | system overview and component responsibilities |
| `SECURITY.md` | guarantees, controls, threat model |
| `DEMO.md` | a four-minute live demo script |
| `README.md` | quick start and tests |

Next: [How it works](/core/how-it-works).