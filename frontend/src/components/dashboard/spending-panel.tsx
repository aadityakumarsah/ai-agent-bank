"use client";

import { useMemo, useState } from "react";
import { Coins, TrendingUp } from "lucide-react";
import type { Agent, Transaction } from "@/lib/types";
import { ProgressRing } from "@/components/ui/progress-ring";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import { formatUsdc, percentOf } from "@/lib/utils";
import { spentTodayForAgent } from "@/lib/risk";
import { cn } from "@/lib/utils";

function SpendingMetric({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className="flex items-center justify-between border-b border-border/60 py-2 last:border-0">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span
        className={cn(
          "font-semibold tabular-nums",
          tone === "destructive"
            ? "text-destructive"
            : tone === "warning"
              ? "text-warning"
              : tone === "success"
                ? "text-success"
                : "text-foreground"
        )}
      >
        {value}
      </span>
    </div>
  );
}

export function SpendingPanel({
  agents,
  transactions,
}: {
  agents: Agent[];
  transactions: Transaction[];
}) {
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const selected = useMemo(() => {
    if (agents.length === 0) return null;
    const target = selectedId ?? agents[0].id;
    return agents.find((a) => a.id === target) ?? agents[0];
  }, [agents, selectedId]);

  if (!selected) {
    return (
      <div className="flex flex-col gap-5 rounded-xl border border-border bg-card p-5">
        <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <TrendingUp className="h-4 w-4" />
          Agent spending will appear here once you create agents.
        </div>
      </div>
    );
  }

  const dailyLimit = selected.policies?.max_per_day ?? 0;
  const spent = transactions ? spentTodayForAgent(transactions, selected.id) : 0;
  const remaining = Math.max(0, dailyLimit - spent);
  const pct = percentOf(spent, dailyLimit);
  const ringTone = pct >= 85 ? "destructive" : pct >= 60 ? "warning" : "primary";

  return (
    <div className="flex flex-col gap-5 rounded-xl border border-border bg-card p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-foreground">Agent Spending</h2>
          <p className="text-xs text-muted-foreground">
            Daily policy budget utilization
          </p>
        </div>
        {agents.length > 1 && (
          <div className="flex flex-wrap gap-1.5">
            {agents.slice(0, 8).map((a) => (
              <button
                key={a.id}
                onClick={() => setSelectedId(a.id)}
                className={cn(
                  "rounded-full border px-2.5 py-1 text-[11px] font-medium transition-colors",
                  selected.id === a.id
                    ? "border-primary/40 bg-primary/10 text-primary"
                    : "border-border bg-card text-muted-foreground hover:text-foreground"
                )}
              >
                {a.name}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="flex flex-col items-center gap-6 sm:flex-row sm:gap-8">
        <div className="relative">
          <ProgressRing value={pct} size={168} stroke={13} tone={ringTone as "primary"}>
            <div className="text-center">
              <div className="text-3xl font-bold tracking-tight tabular-nums text-foreground">
                {dailyLimit > 0 ? `${Math.round(pct)}%` : "—"}
              </div>
              <div className="mt-0.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                of daily limit
              </div>
            </div>
          </ProgressRing>
        </div>

        <div className="w-full min-w-0 flex-1">
          {dailyLimit > 0 ? (
            <>
              <div className="rounded-lg border border-border bg-background/40 px-3 py-2">
                <SpendingMetric label="Daily limit" value={formatUsdc(dailyLimit)} />
                <SpendingMetric label="Spent today" value={formatUsdc(spent)} tone={pct >= 85 ? "destructive" : undefined} />
                <SpendingMetric label="Remaining" value={formatUsdc(remaining)} tone={pct >= 85 ? "warning" : "success"} />
              </div>
              <div className="mt-3">
                <Progress value={pct} tone={ringTone as "primary"} />
                <div className="mt-1.5 flex justify-between text-[10px] text-muted-foreground">
                  <span>
                    Resets at midnight · agent: <span className="font-medium text-foreground">{selected.name}</span>
                  </span>
                  <span className="tabular-nums">
                    {formatUsdc(spent)} / {formatUsdc(dailyLimit)}
                  </span>
                </div>
              </div>
            </>
          ) : (
            <div className="flex items-start gap-2.5 rounded-lg border border-warning/30 bg-warning/5 px-3 py-3 text-sm text-muted-foreground">
              <Coins className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
              <div>
                No daily limit set for{" "}
                <span className="font-medium text-foreground">{selected.name}</span>. Set a
                policy to bound daily spending.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function SpendingPanelSkeleton() {
  return (
    <div className="flex flex-col gap-5 rounded-xl border border-border bg-card p-5">
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-3 w-48" />
        </div>
        <Skeleton className="h-6 w-24 rounded-full" />
      </div>
      <div className="flex items-center gap-8">
        <Skeleton className="h-[168px] w-[168px] rounded-full" />
        <div className="flex-1 space-y-3">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-full" />
        </div>
      </div>
    </div>
  );
}