"use client";

import { useMemo, useState } from "react";
import {
  Play,
  Bot,
  Loader2,
  ShieldCheck,
  CircleDollarSign,
  TriangleAlert,
  Link2,
} from "lucide-react";
import { useBankData } from "@/hooks/use-bank-data";
import { useConfigStatus } from "@/hooks/use-config-status";
import { Button } from "@/components/ui/button";
import { Panel } from "@/components/ui/panel";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { TracePlayer } from "@/components/marketplace/trace-timeline";
import { api } from "@/lib/api";
import { formatUsdc, shortAddress, explorerTxUrl, cn } from "@/lib/utils";
import type { DemoResult } from "@/lib/types";

export type DemoKind = "killer" | "failed";

const DEMO_META: Record<
  DemoKind,
  {
    task: string;
    amount: number;
    title: string;
    description: string;
  }
> = {
  killer: {
    task: "Find the best Solana RPC provider and return the recommendation.",
    amount: 0.02,
    title: "Autonomous purchase",
    description:
      "The agent requests an API, gets 402 Payment Required, asks the bank, the policy engine approves ($0.02 < $20 limit), USDC payment executes, and the API returns data.",
  },
  failed: {
    task: "Purchase premium market data for $50 to price a token.",
    amount: 50,
    title: "Blocked by policy",
    description:
      "The agent tries a $50 API payment, but max per-transaction is $20. The policy engine blocks it — the agent can continue searching for a cheaper service.",
  },
};

function PolicyChecks({ checks }: { checks: DemoResult["checks"] }) {
  if (!checks?.length) return null;
  const detailOf = (c: (typeof checks)[number]): string => {
    if (typeof c.detail === "string" && c.detail) return c.detail;
    const parts: string[] = [];
    if (c.requested !== undefined) parts.push(`req ${c.requested}`);
    if (c.allowed !== undefined) parts.push(`allowed ${c.allowed}`);
    return parts.join(" · ");
  };
  return (
    <div className="mt-4">
      <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
        Policy engine checks
      </div>
      <div className="flex flex-col gap-1.5">
        {checks.map((c, i) => {
          const detail = detailOf(c);
          return (
            <div
              key={i}
              className="flex items-center justify-between gap-3 rounded-lg border border-border bg-secondary/30 px-3 py-2"
            >
              <span className="text-xs font-medium text-foreground">{c.name}</span>
              <div className="flex items-center gap-2">
                {detail && (
                  <span className="font-mono text-[11px] text-muted-foreground">
                    {detail.length > 42 ? `${detail.slice(0, 40)}…` : detail}
                  </span>
                )}
                <span
                  className={cn(
                    "rounded px-1.5 py-0.5 text-[10px] font-bold uppercase",
                    c.passed ? "bg-success/15 text-success" : "bg-destructive/15 text-destructive"
                  )}
                >
                  {c.passed ? "pass" : "fail"}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ProofBlock({ result }: { result: DemoResult }) {
  const { status } = useConfigStatus();
  const tx = result.transaction;
  const proof = result.proof;
  const network = status?.solana_network === "mainnet-beta" ? "mainnet-beta" : "devnet";

  if (result.flow === "completed" && proof && tx?.tx_hash) {
    const url = proof.explorer_url ?? (!proof.simulated ? explorerTxUrl(proof.tx_hash, network) : null);
    return (
      <div className="mt-4 rounded-lg border border-success/25 bg-success/5 p-3">
        <div className="mb-1.5 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-success">
          <CircleDollarSign className="h-3.5 w-3.5" />
          Payment proof
        </div>
        <div className="flex flex-wrap items-center gap-2 font-mono text-xs">
          <span className="font-semibold text-foreground">{tx.recipient_name}</span>
          <span className="text-muted-foreground">·</span>
          <span>{shortAddress(tx.tx_hash, 8)}</span>
          {proof.simulated ? (
            <Badge variant="warning" className="gap-1 text-[9px]">
              SIMULATED
            </Badge>
          ) : (
            url && (
              <a
                href={url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-primary hover:underline"
              >
                <Link2 className="h-3 w-3" />
                explorer
              </a>
            )
          )}
        </div>
      </div>
    );
  }
  if (result.flow === "blocked" || result.flow === "approval_required") {
    return (
      <div className="mt-4 rounded-lg border border-destructive/25 bg-destructive/5 p-3">
        <div className="mb-1 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-destructive">
          <ShieldCheck className="h-3.5 w-3.5" />
          No payment executed
        </div>
        <p className="text-xs text-muted-foreground">
          {result.flow === "approval_required"
            ? "The payment requires human approval before any USDC is spent."
            : "The policy engine refused the payment. Zero USDC was spent."}
        </p>
      </div>
    );
  }
  return null;
}

export function DemoSection({
  kind,
  onSelectService,
}: {
  kind: DemoKind;
  onSelectService?: () => void;
}) {
  const { agents, loading, error, load } = useBankData();
  const [agentId, setAgentId] = useState<number | null>(null);
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [result, setResult] = useState<DemoResult | null>(null);
  const [key, setKey] = useState(0);

  const activeAgents = useMemo(
    () => agents.filter((a) => a.status === "active"),
    [agents]
  );
  const selectedAgent = useMemo(
    () => agents.find((a) => a.id === agentId),
    [agents, agentId]
  );
  const meta = DEMO_META[kind];
  const hasPolicyAndFunds =
    !!selectedAgent?.policies && (selectedAgent.policies.max_per_transaction ?? 0) > 0;

  const run = async () => {
    if (!agentId) return;
    setRunning(true);
    setRunError(null);
    setResult(null);
    setKey((k) => k + 1);
    try {
      const res =
        kind === "killer"
          ? await api.runKillerDemo(agentId, meta.amount)
          : await api.runFailedDemo(agentId, meta.amount);
      setResult(res);
      if (res.flow === "completed") onSelectService?.();
    } catch (e) {
      setRunError(e instanceof Error ? e.message : "Demo failed to run");
    } finally {
      setRunning(false);
    }
  };

  if (loading && agents.length === 0) {
    return (
      <Panel>
        <EmptyState icon={Loader2} title="Loading agents…" description="" />
      </Panel>
    );
  }

  if (error) {
    return <ErrorState description={error} onRetry={() => void load()} />;
  }

  if (agents.length === 0) {
    return (
      <Panel>
        <EmptyState
          icon={Bot}
          title="Create an agent first"
          description="You need a funded agent with a policy to see the agent pay for services."
        />
      </Panel>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Control bar */}
      <Panel className="border-primary/20">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <Badge variant={kind === "killer" ? "success" : "destructive"} className="gap-1">
                <TriangleAlert className="h-3 w-3" />
                {kind === "killer" ? "AUTO-APPROVED" : "POLICY BLOCK"}
              </Badge>
              <span className="text-sm font-semibold text-foreground">{meta.task}</span>
            </div>
            <div className="mt-1 text-xs text-muted-foreground">{meta.description}</div>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <div>
              <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                Run with agent
              </label>
              <select
                value={agentId ?? ""}
                onChange={(e) => setAgentId(Number(e.target.value))}
                className="h-9 w-full rounded-md border border-input bg-card px-3 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:w-56"
              >
                <option value="" disabled>
                  Select agent…
                </option>
                {activeAgents.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name} · {formatUsdc(a.balance)}
                  </option>
                ))}
              </select>
            </div>
            <Button
              onClick={run}
              disabled={!agentId || running}
              className="mt-4 sm:mt-6"
              variant={kind === "killer" ? "default" : "secondary"}
            >
              {running ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              {running ? "Running…" : result ? "Re-run demo" : "Run demo"}
            </Button>
          </div>
        </div>

        {selectedAgent && !hasPolicyAndFunds && (
          <div className="mt-3 flex items-start gap-2 rounded-lg border border-warning/25 bg-warning/5 p-2.5 text-xs text-muted-foreground">
            <TriangleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-warning" />
            <span>
              This agent has no policy with a per-transaction limit. The block demo
              relies on {formatUsdc(20)} max per transaction. Set a policy on the{" "}
              <a href="/policies" className="text-primary underline">
                Policies
              </a>{" "}
              page for the most realistic result.
            </span>
          </div>
        )}
      </Panel>

      {runError && <ErrorState description={runError} onRetry={() => void run()} />}

      {result ? (
        <>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
            {/* Trace */}
            <Panel
              title={kind === "killer" ? "Execution trace" : "Blocked trace"}
              description="Full agent → bank → policy → USDC → API flow"
            >
              <TracePlayer key={key} steps={result.trace} autoPlay />
            </Panel>

            {/* Result summary */}
            <div className="flex flex-col gap-4">
              <Panel
                title={
                  result.flow === "completed"
                    ? "Task completed"
                    : result.flow === "blocked"
                      ? "Payment blocked"
                      : "Payment halted"
                }
                description={
                  result.flow === "completed"
                    ? "The agent paid and got its answer."
                    : "No USDC was spent."
                }
              >
                {result.flow === "completed" && result.summary ? (
                  <div className="rounded-lg border border-success/25 bg-success/5 p-3">
                    <div className="mb-1 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-success">
                      <Bot className="h-3.5 w-3.5" />
                      Agent recommendation
                    </div>
                    <p className="text-sm leading-relaxed text-foreground">{result.summary}</p>
                  </div>
                ) : (
                  <div className="rounded-lg border border-destructive/25 bg-destructive/5 p-3">
                    <div className="mb-1 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-destructive">
                      <ShieldCheck className="h-3.5 w-3.5" />
                      {result.flow === "blocked" ? "Blocked" : "Needs approval"}
                    </div>
                    {result.reason ? (
                      <p className="text-sm leading-relaxed text-foreground">{result.reason}</p>
                    ) : (
                      <p className="text-xs text-muted-foreground">
                        Transaction above approval threshold.
                      </p>
                    )}
                  </div>
                )}
                {result.suggestion && (
                  <div className="mt-3 flex items-start gap-2 rounded-lg border border-border bg-secondary/40 p-2.5 text-xs text-muted-foreground">
                    <Bot className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
                    <span>{result.suggestion}</span>
                  </div>
                )}
              </Panel>

              <Panel title="Settlement" description="The money moved — or didn't.">
                <div className="flex flex-col gap-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Requested</span>
                    <span className="font-mono font-semibold text-foreground">
                      {formatUsdc(meta.amount)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Outcome</span>
                    <Badge
                      variant={result.flow === "completed" ? "success" : "destructive"}
                      className="gap-1"
                    >
                      <CircleDollarSign className="h-3 w-3" />
                      {result.flow === "completed" ? (
                        <>{formatUsdc(result.transaction?.amount ?? meta.amount)} USDC paid</>
                      ) : (
                        "$0.00 USDC spent"
                      )}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Agent</span>
                    <span className="truncate font-mono text-foreground">
                      {selectedAgent?.name ?? result.agent_name}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Service</span>
                    <span className="truncate font-mono text-foreground">
                      {result.service?.name ?? meta.title}
                    </span>
                  </div>
                </div>
                <ProofBlock result={result} />
                <PolicyChecks checks={result.checks} />
              </Panel>
            </div>
          </div>
        </>
      ) : (
        <Panel bodyClassName="py-10 text-center">
          <div className="flex flex-col items-center gap-2">
            <div className="flex h-11 w-11 items-center justify-center rounded-full border border-border bg-secondary text-primary">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <div className="text-sm font-semibold text-foreground">
                {kind === "killer"
                  ? "Watch the agent pay for an API in real time."
                  : "Watch the policy engine stop an uncontrollable payment."}
              </div>
              <div className="mt-1 text-xs text-muted-foreground">
                Select an agent above and press run.
              </div>
            </div>
          </div>
        </Panel>
      )}
    </div>
  );
}