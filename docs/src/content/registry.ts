export interface PageMeta {
  /** URL segment. Route is `/{group}/{slug}`. */
  slug: string;
  title: string;
  description: string;
  keywords?: string[];
}

export interface Group {
  id: string;
  label: string;
  pages: PageMeta[];
}

export const DOCS_VERSION = "Part 10 / 10";
export const REPO_URL = "https://github.com/aadityakumarsah/birgro";

export const GROUPS: Group[] = [
  {
    id: "get-started",
    label: "Get started",
    pages: [
      { slug: "welcome", title: "Welcome", description: "What AI Agent Bank is, what it protects, and how the pieces fit together." },
      { slug: "quickstart", title: "Quickstart", description: "Run the backend and frontend locally and make your first payment in about five minutes." },
      { slug: "install", title: "Install & run locally", description: "Clone, configure, and run the full stack with both mock and real modes." },
      { slug: "repo", title: "Repository layout", description: "Where everything lives in the repo: backend, frontend, SQL, docs." },
    ],
  },
  {
    id: "core",
    label: "Core concepts",
    pages: [
      { slug: "how-it-works", title: "How it works", description: "From human-funded wallet to policy-gated agent payment — the full lifecycle." },
      { slug: "agents", title: "Agents", description: "What an agent is, agent statuses, and the agent lifecycle." },
      { slug: "wallets", title: "Agent wallets & escrow", description: "How agent funds work: escrow addresses, balances, and derived keys." },
      { slug: "policies", title: "Policies", description: "The per-agent permission config: limits, categories, recipients, approvals." },
      { slug: "tasks", title: "Tasks & task runs", description: "How an agent turns a task into a proposal — and when money moves." },
    ],
  },
  {
    id: "policies",
    label: "Policy engine",
    pages: [
      { slug: "engine", title: "How the engine works", description: "Deterministic, ordered checks that run on every single payment proposal." },
      { slug: "limits", title: "Spending limits", description: "Per-transaction, per-day, and rolling 30-day monthly caps — enforced twice." },
      { slug: "trust", title: "Recipient trust", description: "Known providers, address allowlists, and the human-transfer block." },
      { slug: "approvals", title: "Human approvals", description: "Payments above the threshold pause for the human. No money moves without you." },
      { slug: "risk", title: "Risk scoring", description: "The transparent, rule-based 0–100 risk score behind every decision." },
    ],
  },
  {
    id: "payments",
    label: "Payments",
    pages: [
      { slug: "overview", title: "Payments overview", description: "One guarded payment path: idempotency, policy, balance check, execution." },
      { slug: "usdc", title: "USDC on Solana", description: "Network, mint addresses, decimals, and how transfers are built and signed." },
      { slug: "funding", title: "Funding & payment requests", description: "Funding an agent from your wallet and the reviewable payment flow." },
      { slug: "ledger", title: "Transaction ledger", description: "Transaction states, idempotency keys, and the immutable audit trail." },
      { slug: "marketplace", title: "Service payments", description: "The service directory and autonomous purchase flow." },
      { slug: "x402", title: "x402 integration", description: "The simplified, self-labelled x402-style request–payment–proof flow." },
    ],
  },
  {
    id: "security",
    label: "Security",
    pages: [
      { slug: "security", title: "Security model", description: "Six guarantees: no keys to the AI, no payment without policy, humans stay in control." },
      { slug: "threat", title: "Threat model", description: "The threats this system defends against and the mitigations for each." },
      { slug: "audit", title: "Audit trail", description: "Append-only audit events for every action, plus the transaction log." },
      { slug: "keys", title: "Private keys & secrets", description: "Master key, derived escrow keys, and Fernet-encrypted LLM keys." },
      { slug: "kill", title: "Pause, revoke & kill switch", description: "Instant human control: suspend, kill, and the DEMO_MODE gate." },
    ],
  },
  {
    id: "guides",
    label: "Guides",
    pages: [
      { slug: "first-agent", title: "Create your first agent", description: "Connect a wallet, create an agent, and give it a policy." },
      { slug: "fund", title: "Fund an agent", description: "Mock funding vs. signing a real USDC transfer to the agent's escrow." },
      { slug: "policy", title: "Configure a policy", description: "Set limits, categories, recipient rules, and the approval threshold." },
      { slug: "task", title: "Run your first task", description: "Give an agent a job and watch the proposal — payment or response — happen." },
      { slug: "approvals", title: "Handle approvals", description: "Approve or reject paused payments from the Approvals page." },
      { slug: "byo-key", title: "Bring your own LLM key", description: "Attach your own OpenAI, Anthropic, or Google key from Settings." },
      { slug: "scenarios", title: "One-click demo scenarios", description: "Four scripted journeys that show every policy outcome." },
      { slug: "realmode", title: "Go live on devnet", description: "Switch from simulated to real Solana devnet USDC, safely." },
    ],
  },
  {
    id: "api",
    label: "API reference",
    pages: [
      { slug: "overview", title: "API overview", description: "Base URL, error shapes, and how to call the API from code." },
      { slug: "status", title: "Status & health", description: "GET /health and GET /api/v1/status." },
      { slug: "users", title: "Users", description: "Create and fetch the wallet-scoped user records." },
      { slug: "agents", title: "Agents", description: "Create, list, fund, update policy, pause, resume, and kill agents." },
      { slug: "transactions", title: "Transactions", description: "List, fetch, approve, and reject wallet transactions." },
      { slug: "runs", title: "Task runs", description: "Run an agent task and list a wallet's task runs." },
      { slug: "services", title: "Services", description: "The marketplace directory and the payment–proof flow." },
      { slug: "llm-keys", title: "LLM keys", description: "Wallet-scoped, encrypted end-user LLM provider keys." },
      { slug: "demo", title: "Demo endpoints", description: "One-click scenarios and the blocked-transaction checker." },
      { slug: "errors", title: "Error codes", description: "Every stable error code and the response shape." },
    ],
  },
  {
    id: "ops",
    label: "Data & operations",
    pages: [
      { slug: "architecture", title: "Architecture", description: "System overview: frontend, backend, policy engine, payment service, data." },
      { slug: "database", title: "Database & migrations", description: "Tables, enums, Alembic migrations, SQLite vs PostgreSQL, and the SQL folder." },
      { slug: "env", title: "Environment variables", description: "Full reference for backend and frontend configuration." },
      { slug: "observability", title: "Logging, limits & errors", description: "Structured JSON logs, rate limiters, idempotency, and error handling." },
      { slug: "tests", title: "Testing", description: "Pytest suite, smoke test, and frontend type checks." },
    ],
  },
  {
    id: "advanced",
    label: "Advanced & project",
    pages: [
      { slug: "production", title: "Production checklist", description: "Everything to verify before running with real money." },
      { slug: "faq", title: "FAQ", description: "Frequent questions about modes, keys, limits, and coverage." },
      { slug: "roadmap", title: "Roadmap", description: "What is real today, what is experimental, and what is planned." },
      { slug: "contributing", title: "Contributing", description: "How to run, test, and extend the codebase." },
    ],
  },
];

const FLAT: { group: Group; page: PageMeta }[] = GROUPS.flatMap((g) =>
  g.pages.map((p) => ({ group: g, page: p }))
);

export function allPages(): { group: Group; page: PageMeta }[] {
  return FLAT;
}

export function pageRoute(groupId: string, slug: string): string {
  return `/${groupId}/${slug}`;
}

export function findPage(
  groupId: string,
  slug: string
): { group: Group; page: PageMeta } | undefined {
  return FLAT.find((e) => e.group.id === groupId && e.page.slug === slug);
}

export function prevNext(
  groupId: string,
  slug: string
): { prev?: { to: string; title: string }; next?: { to: string; title: string } } {
  const idx = FLAT.findIndex((e) => e.group.id === groupId && e.page.slug === slug);
  if (idx === -1) return {};
  const prev = FLAT[idx - 1];
  const next = FLAT[idx + 1];
  return {
    prev: prev
      ? { to: pageRoute(prev.group.id, prev.page.slug), title: prev.page.title }
      : undefined,
    next: next
      ? { to: pageRoute(next.group.id, next.page.slug), title: next.page.title }
      : undefined,
  };
}

export function searchIndex() {
  return FLAT.map((e) => ({
    to: pageRoute(e.group.id, e.page.slug),
    group: e.group.label,
    title: e.page.title,
    description: e.page.description,
    keywords: e.page.keywords ?? [],
  }));
}