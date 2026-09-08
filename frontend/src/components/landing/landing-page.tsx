"use client";

import { useRouter } from "next/navigation";
import { ShieldCheck, Zap, HandCoins, Landmark, ArrowRight } from "lucide-react";
import { useWalletConnection } from "@/components/wallet/wallet-context";

const POLICY_CHIPS = [
  { label: "Per transaction", value: "$20", tone: "text-foreground border-border bg-card" },
  { label: "Per day", value: "$100", tone: "text-foreground border-border bg-card" },
  { label: "Per month", value: "$1,000", tone: "text-foreground border-border bg-card" },
  { label: "Above $20 → human approval", value: "REQUIRED", tone: "text-warning border-warning/30 bg-warning/10" },
  { label: "Human transfers", value: "BLOCKED", tone: "text-destructive border-destructive/30 bg-destructive/10" },
  { label: "Trading", value: "BLOCKED", tone: "text-destructive border-destructive/30 bg-destructive/10" },
];

const FLOW = [
  { step: "YOU", sub: "Fund $500 USDC", icon: Landmark, tone: "text-primary border-primary/30 bg-primary/10" },
  { step: "AI AGENT", sub: "ResearchBot", icon: Zap, tone: "text-info border-info/30 bg-info/10" },
  { step: "POLICY ENGINE", sub: "Deterministic rules", icon: ShieldCheck, tone: "text-warning border-warning/30 bg-warning/10" },
  { step: "SOLANA", sub: "USDC escrow", icon: HandCoins, tone: "text-success border-success/30 bg-success/10" },
  { step: "SERVICES", sub: "RPC · APIs · data", icon: ArrowRight, tone: "text-muted-foreground border-border bg-secondary" },
];

export function LandingPage() {
  const router = useRouter();
  const { openWalletSelect } = useWalletConnection();

  const launch = () => {
    openWalletSelect(() => router.push("/dashboard"));
  };

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="flex items-center justify-between border-b border-border px-5 py-4 sm:px-8">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Landmark className="h-4.5 w-4.5" />
          </div>
          <div className="leading-tight">
            <div className="text-[15px] font-bold tracking-tight text-foreground">AI Agent Bank</div>
            <div className="text-[10px] text-muted-foreground">Programmable financial permissions for AI agents</div>
          </div>
        </div>
        <button
          onClick={launch}
          className="inline-flex h-9 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          Connect wallet
        </button>
      </header>

      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col items-center px-5 py-16 sm:px-8">
        <div className="text-center">
          <div className="mx-auto mb-5 inline-flex items-center gap-1.5 rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-[11px] font-semibold text-primary">
            <Zap className="h-3.5 w-3.5" />
            Give AI money. Don&apos;t give it unlimited control.
          </div>
          <h1 className="mx-auto max-w-3xl text-4xl font-bold leading-tight tracking-tight text-foreground sm:text-5xl">
            AI AGENT BANK
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-base leading-relaxed text-muted-foreground">
            An economic permission layer for autonomous AI agents. AI agents can act
            autonomously, but they should not have unlimited economic authority. Fund
            them, bound them with a deterministic policy engine, and stay the final
            authority over every payment.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <button
              onClick={launch}
              className="inline-flex h-11 items-center gap-2 rounded-lg bg-primary px-6 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90"
            >
              Connect wallet
            </button>
            <a
              href="#how-it-works"
              className="inline-flex h-11 items-center gap-2 rounded-lg border border-border bg-card px-6 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
            >
              How It Works
            </a>
          </div>
        </div>

        {/* Policy chips */}
        <div className="mt-12 flex flex-wrap items-center justify-center gap-2">
          {POLICY_CHIPS.map((chip) => (
            <span
              key={chip.label}
              className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs ${chip.tone}`}
            >
              <span className="font-medium">{chip.label}</span>
              <span className="font-bold tabular-nums">{chip.value}</span>
            </span>
          ))}
        </div>

        {/* Flow */}
        <div id="how-it-works" className="mt-16 flex w-full flex-col items-center scroll-mt-8">
          <h2 className="text-sm font-semibold uppercase tracking-widest text-muted-foreground">
            One payment, end to end
          </h2>
          <div className="mt-6 grid w-full grid-cols-1 items-stretch gap-3 sm:grid-cols-5">
            {FLOW.map((node, i) => (
              <div key={node.step} className="flex flex-col gap-3 sm:flex-row sm:items-stretch">
                <div
                  className={`flex flex-col justify-center gap-2 rounded-xl border p-4 ${node.tone} ${
                    i % 2 === 0 ? "" : "sm:mt-3"
                  }`}
                >
                  <node.icon className="h-5 w-5" />
                  <div className="text-sm font-bold tracking-wide text-foreground">{node.step}</div>
                  <div className="text-xs text-muted-foreground">{node.sub}</div>
                </div>
                {i < FLOW.length - 1 && (
                  <div className="flex items-center justify-center text-muted-foreground sm:px-0.5">
                    <ArrowRight className="h-4 w-4 rotate-90 sm:rotate-0" />
                  </div>
                )}
              </div>
            ))}
          </div>
          <p className="mt-6 max-w-xl text-center text-xs leading-relaxed text-muted-foreground">
            The agent <span className="text-foreground">proposes</span>. The policy engine{" "}
            <span className="text-foreground">decides</span> — in deterministic code, never by
            AI judgment. The blockchain <span className="text-foreground">executes</span>.
            Humans stay in control.
          </p>
        </div>
      </main>

      <footer className="border-t border-border py-6">
        <p className="text-center text-xs text-muted-foreground">
          AI Agent Bank — the AI proposes, the policy engine decides, the blockchain executes.
        </p>
      </footer>
    </div>
  );
}