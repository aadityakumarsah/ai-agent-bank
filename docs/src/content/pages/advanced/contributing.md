# Contributing

Guidance for working in this repo and on these docs. It is short on purpose —
the codebase conventions do the real teaching.

## Working on the backend

- Run the API: `cd backend && uvicorn app.main:app --reload --port 8000`
  (reads `backend/.env`).
- Run tests: `cd backend && pytest -q`.
- Add a migration for schema changes: `cd backend && alembic revision --autogenerate -m "…"`
  then `alembic upgrade head`.
- Prefer the service layer: money logic belongs in `app/services/*`, not routers.

## Working on the dashboard

```bash
cd frontend && npm install && npm run dev    # :3000
```

`NEXT_PUBLIC_API_URL` defaults to `http://localhost:8000`. Keep types in
`lib/types.ts` and API calls in `lib/api.ts`.

## Working on these docs

```bash
cd docs && npm install && npm run dev        # :3001
```

- Content lives in `docs/src/content/pages/<group>/<slug>.md`.
- Navigation, search, and prev/next metadata are all derived from
  `docs/src/content/registry.ts` — register a new page there.
- Markdown supports GitHub-style callouts (`[!NOTE]` / `[!WARNING]` /
  `[!IMPORTANT]` / `[!TIP]`) and GFM tables.
- Build & typecheck: `npm run build` (runs `tsc --noEmit && vite build`).

Read `docs/README.md` for the full run instructions.

## Documentation rules we hold ourselves to

1. **Never document features that don't exist.** No fake endpoints, no invented
   SDKs, no imagined webhooks — those are marked planned/absent.
2. **Never show real secrets.** Env docs use `VARIABLE=` or a substitute value,
   never a production key.
3. **Always label mock vs real.** Every money path keeps `mode` and `simulated`.
4. **Fight the code, not the docs.** When docs and code disagree, the docs are
   wrong — update the page, don't paper over it.
5. **x402 is labelled.** It's a simplified, self-labelled demo, not
   wire-compatible.

## Before you merge

- `npm run build` in `docs` passes (typecheck + build).
- `pytest` in `backend` passes for backend changes.
- The demo story (mock + devnet) still reads honestly after the diff.

> [!IMPORTANT]
> The parent repo includes the whole desktop workspace; commit only what belongs
> to this change and keep secrets out of every diff.

Next: nothing — you've reached the end of the guide. Back to [Welcome](/get-started/welcome).