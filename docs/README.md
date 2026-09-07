# AI Agent Bank — Documentation

A production-quality Vite + React + TypeScript documentation site for the
AI Agent Bank project. It is isolated from the backend and frontend, and is the
authoritative reference for how the real codebase works.

## Quick start

```bash
cd docs
npm install      # 180 packages
npm run dev      # http://localhost:3001
```

Build:

```bash
npm run build    # tsc --noEmit && vite build → dist/
```

Typecheck only:

```bash
npx tsc --noEmit
```

## What's inside

```
docs/
├── index.html                 # SPA shell (anti-FOUC theme script inlined)
├── vite.config.ts             # port 3001 strictPort
├── tsconfig.json
├── src/
│   ├── main.tsx               # React root, BrowserRouter
│   ├── App.tsx                # Route table: /, /:group/:slug, * (404)
│   ├── lib/
│   │   ├── theme.ts           # System/light/dark mode with localStorage
│   │   ├── search.ts          # Lightweight search index
│   │   └── content.ts         # import.meta.glob reads all Markdown pages
│   ├── hooks/useTheme.ts      # Toggle + system-media detection
│   ├── content/
│   │   ├── registry.ts        # All pages, groups, SEO metadata, helpers
│   │   └── pages/**/*.md      # 52 authored Markdown pages
│   ├── components/
│   │   ├── TopNav             # Hamburger drawer nav, search trigger (⌘K / Ctrl+K)
│   │   ├── Sidebar            # Grouped nav, backdrop on mobile
│   │   ├── SearchModal        # Keyboard-navigated full-text search
│   │   ├── ThemeToggle        # Cycles system → light → dark → system
│   │   ├── Markdown           # GFM, code highlighting (Prism), callouts, heading anchors
│   │   ├── CodeBlock          # Highlighted code with copy button
│   │   ├── Toc                # Right-rail table of contents (scroll-spy)
│   │   ├── Breadcrumbs        # Group → page breadcrumb
│   │   ├── PrevNext           # Previous / next navigation
│   │   ├── DocPage            # Page layout wrapper (SEO, Toc, prev/next)
│   │   ├── NotFoundPage       # Custom 404
│   │   └── Footer             # Repo link, version
│   └── styles/
│       └── app.css            # Full theme (light + dark), Prism tokens, responsive
└── dist/                      # Built output (served by any static host)
```

## Design principles

- **Light-first premium dev-tool aesthetic** — white/very-light background, dark
  text, soft indigo accent, subtle shadows. No SaaS landing page.
- **Codebase-accurate** — every page documents the actual implementation; nothing
  fabricated, no placeholder features.
- **Fully functional controls** — search works, theme toggle works, sidebar
  drawer works on mobile, copy buttons work, ToC highlights the current section.
- **Isolated** — this site is an independent process on `:3001`; it has zero
  runtime dependency on the backend or Next.js frontend.

## Page structure

Pages are organized into 9 groups:

| Group | Pages | What it covers |
|---|---|---|
| Get started | 4 | Welcome, Quickstart, Install, Repository layout |
| Core concepts | 5 | How it works, Agents, Wallets, Policies, Tasks |
| Policy engine | 5 | Engine, Limits, Trust, Approvals, Risk |
| Payments | 6 | Overview, USDC, Funding, Ledger, Marketplace, x402 |
| Security | 5 | Security model, Threats, Audit, Keys, Kill switch |
| Guides | 8 | First agent, Fund, Policy, Task, Approvals, BYO key, Demos, Devnet |
| API reference | 10 | Overview, Status, Users, Agents, Transactions, Runs, Services, LLM keys, Demo, Errors |
| Operations | 5 | Architecture, Database, Env vars, Observability, Tests |
| Advanced | 4 | Production, FAQ, Roadmap, Contributing |

Total: **52 pages** with a single source of truth in `src/content/registry.ts`.

## Adding a new page

1. Create `src/content/pages/<group>/<slug>.md` with a top-level `# Title`.
2. Add the page to the corresponding group in `src/content/registry.ts`.
3. Run `npm run build` — the glob automatically picks up the new `.md` file.

All navigation, sidebar, search, prev/next, and breadcrumbs update automatically
from the registry.

## Notes

- The large JS bundle is from PrismJS language support. To reduce size, use
  dynamic `import()` for `CodeBlock` and trim unused languages.
- This site uses Vite's `import.meta.glob` to read Markdown files at build time
  and serve them as static strings in the JS bundle — no server-side rendering,
  no CMS, no external dependencies.
