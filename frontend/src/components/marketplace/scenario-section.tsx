"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Play,
  Loader2,
  Sparkles,
  Check,
  TriangleAlert,
  UserRoundCheck,
  Wallet,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Panel } from "@/components/ui/panel";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { TracePlayer } from "@/components/marketplace/trace-timeline";
import { api } from "@/lib/api";
import { formatUsdc, shortAddress, cn } from "@/lib/utils";
import type { DemoScenario, DemoScenarioRunResult } from "@/lib/types";

const OUTCOME_TONE: Record<
  DemoScenarioRunResult["flow"],
  "success" | "destructive" | "info" | "warning"
> = {
  completed: "success",
  blocked: "destructive",
  approval_required: "info",
  failed: "destructive",
};

const OUTCOME_LABEL: Record<DemoScenarioRunResult["flow"], string> = {
  completed: "Completed",
  blocked: "Blocked",
  approval_required: "Approval required",
  failed: "Failed",
};

function ScenarioCard({
  scenario,
  onRun,
  onApprove,
  running,
  result,
  error,
}: {
  scenario: DemoScenario;
  onRun: () => void;
  onApprove: () => void;
  running: boolean;
  result: DemoScenarioRunResult | null;
  error: string | null;
}) {
  const tier = (bar: string) => ({
    completed: "border-success/30 bg-success/5 text-success",
    blocked: "border-destructive/30 bg-destructive/5 text-destructive",
    approval_required: "border-primary/30 bg-primary/5 text-primary",
    failed: "border-destructive/30 bg-destructive/5 text-destructive",
  })[bar];

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className={cn("gap-1", tier(scenario.outcome))}>
              <Sparkles className="h-3 w-3" />
              {scenario.badge}
            </Badge>
          </div>
          <h4 className="mt-1.5 text-sm font-semibold text-foreground">{scenario.title}</h4>
        </div>
        <span className="shrink-0 font-mono text-sm font-semibold text-foreground">
          {formatUsdc(scenario.amount)}
        </span>
      </div>

      <p className="text-xs leading-relaxed text-muted-foreground">{scenario.task}</p>

      <div className="mt-auto flex items-center gap-2 pt-1">
        <Button
          onClick={onRun}
          disabled={running}
          variant={result?.flow === "completed" ? "secondary" : "default"}
          className="flex-1"
        >
          {running ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Play className="h-4 w-4" />
          )}
          {running ? "Running…" : result ? "Re-run" : "Run scenario"}
        </Button>
        {result?.can_approve && (
          <Button onClick={onApprove} variant="success">
            <Check className="h-4 w-4" />
            Approve payment
          </Button>
        )}
      </div>

      {error && <div className="text-[11px] text-destructive">{error}</div>}

      {result && (
        <div className="mt-1 border-t border-border pt-3">
          <div className="mb-2 flex items-center justify-between gap-2">
            <Badge variant={OUTCOME_TONE[result.flow]}>{OUTCOME_LABEL[result.flow]}</Badge>
            {result.flow === "completed" && result.transaction?.tx_hash ? (
              <span className="font-mono text-[10px] text-muted-foreground">
                {shortAddress(result.transaction.tx_hash, 8)}
              </span>
            ) : (
              <span className="font-mono text-[10px] text-muted-foreground">
                {formatUsdc(result.agent.balance)} left
              </span>
            )}
          </div>
          <TracePlayer steps={result.trace} autoPlay />
        </div>
      )}
    </div>
  );
}

export function ScenarioSection() {
  const [scenarios, setScenarios] = useState<DemoScenario[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [runningId, setRunningId] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, DemoScenarioRunResult>>({});
  const [runErrors, setRunErrors] = useState<Record<string, string>>({});
  const [requestIds, setRequestIds] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listDemoScenarios();
      setScenarios(data.demo_mode ? data.scenarios : []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load demo scenarios");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const run = async (scenario: DemoScenario) => {
    setRunningId(scenario.id);
    setRunErrors((m) => ({ ...m, [scenario.id]: "" }));
    try {
      const clientRequestId = `ui-${Date.now()}`;
      setRequestIds((m) => ({ ...m, [scenario.id]: clientRequestId }));
      const res = await api.runDemoScenario(scenario.id, clientRequestId);
      setResults((m) => ({ ...m, [scenario.id]: res }));
    } catch (e) {
      setRunErrors((m) => ({
        ...m,
        [scenario.id]: e instanceof Error ? e.message : "Scenario failed",
      }));
    } finally {
      setRunningId(null);
    }
  };

  const approve = async (scenario: DemoScenario) => {
    setRunningId(scenario.id);
    setRunErrors((m) => ({ ...m, [scenario.id]: "" }));
    try {
      const res = await api.approveDemoScenario(scenario.id, requestIds[scenario.id]);
      setResults((m) => ({ ...m, [scenario.id]: res }));
    } catch (e) {
      setRunErrors((m) => ({
        ...m,
        [scenario.id]: e instanceof Error ? e.message : "Approval failed",
      }));
    } finally {
      setRunningId(null);
    }
  };

  if (loading && scenarios === null) {
    return (
      <Panel>
        <EmptyState icon={Loader2} title="Loading scenarios…" description="" />
      </Panel>
    );
  }

  if (error) {
    return <ErrorState description={error} onRetry={() => void load()} />;
  }

  if (!scenarios || scenarios.length === 0) {
    return (
      <Panel>
        <EmptyState
          icon={TriangleAlert}
          title="Demo mode is off"
          description="The one-click scenarios are gated behind DEMO_MODE so a live deployment never accidentally runs demo money. Set DEMO_MODE=true (or leave it blank) in the backend .env."
        />
      </Panel>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <Panel className="border-primary/20">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Sparkles className="h-4.5 w-4.5" />
            </div>
            <div>
              <div className="text-sm font-semibold text-foreground">
                One-click demo scenarios
              </div>
              <div className="text-xs text-muted-foreground">
                Each button provisions a deterministic ResearchBot ($100, policy set &nbsp;→&nbsp; run) and walks the real agent → bank → policy → USDC path.
              </div>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 text-[11px] text-muted-foreground">
            <span className="inline-flex items-center gap-1 rounded-md border border-border bg-secondary/40 px-2 py-1">
              <Wallet className="h-3 w-3" /> DemoWallet…1111111
            </span>
            <span className="inline-flex items-center gap-1 rounded-md border border-border bg-secondary/40 px-2 py-1">
              <UserRoundCheck className="h-3 w-3" /> ResearchBot
            </span>
          </div>
        </div>
      </Panel>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {scenarios.map((s) => (
          <ScenarioCard
            key={s.id}
            scenario={s}
            running={runningId === s.id}
            result={results[s.id] ?? null}
            error={runErrors[s.id] ?? null}
            onRun={() => void run(s)}
            onApprove={() => void approve(s)}
          />
        ))}
      </div>
    </div>
  );
}