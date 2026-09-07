"use client";

import Link from "next/link";
import { Bot, ArrowRight } from "lucide-react";
import type { Agent, Transaction } from "@/lib/types";
import { AGENT_STATUS_TONES } from "@/lib/types";
import { AgentStatusBadge } from "@/components/ui/status-badge";
import { Progress } from "@/components/ui/progress";
import { formatUsdc, percentOf } from "@/lib/utils";
import { riskLevel, spentTodayForAgent } from "@/lib/risk";
import { cn } from "@/lib/utils";

export function AgentCard({
  agent,
  transactions,
}: {
  agent: Agent;
  transactions?: Transaction[];
}) {
  const dailyLimit = agent.policies?.max_per_day ?? 0;
  const spentToday = transactions ? spentTodayForAgent(transactions, agent.id) : 0;
  const pct = percentOf(spentToday, dailyLimit);
  const risk = riskLevel(agent);
  const txCount = transactions?.filter((t) => t.agent_id === agent.id).length ?? 0;
  const initial = agent.name.slice(0, 2).toUpperCase();

  return (
    <Link
      href={`/agents/${agent.id}`}
      className={cn(
        "group flex flex-col gap-4 rounded-xl border border-border bg-card p-4 transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-lg hover:shadow-black/20"
      )}
    >
      {/* Header */}
      <div className="flex items-start gap-3">
        <div className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-secondary text-primary">
          <Bot className="h-5 w-5" />
          <span className="absolute -bottom-0.5 -right-0.5 flex h-3 w-3 items-center justify-center rounded-full border border-card bg-background">
            <span
              className={cn(
                "h-1.5 w-1.5 rounded-full",
                agent.status === "active"
                  ? "bg-success"
                  : agent.status === "suspended"
                    ? "bg-warning"
                    : "bg-destructive"
              )}
            />
          </span>
        </div>
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-semibold text-foreground">{agent.name}</div>
          <div className="truncate text-xs text-muted-foreground">{initial} · #{agent.id}</div>
        </div>
        <AgentStatusBadge status={agent.status} />
      </div>

      {/* Balance */}
      <div className="flex items-end justify-between">
        <div>
          <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Balance
          </div>
          <div className="mt-0.5 text-xl font-bold tracking-tight tabular-nums text-foreground">
            {formatUsdc(agent.balance)}
            <span className="ml-1 text-xs font-medium text-muted-foreground">USDC</span>
          </div>
        </div>
        <div className="hidden flex-col items-end sm:flex">
          <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Transactions
          </div>
          <div className="mt-0.5 text-sm font-semibold tabular-nums text-foreground">{txCount}</div>
        </div>
      </div>

      {/* Daily spending */}
      {dailyLimit > 0 ? (
        <div>
          <div className="mb-1.5 flex items-center justify-between text-[11px]">
            <span className="text-muted-foreground">
              Spent <span className="font-semibold text-foreground tabular-nums">{formatUsdc(spentToday)}</span> of{" "}
              {formatUsdc(dailyLimit)} today
            </span>
            <span className="tabular-nums text-muted-foreground">{Math.round(pct)}%</span>
          </div>
          <Progress
            value={pct}
            tone={pct >= 85 ? "destructive" : pct >= 60 ? "warning" : "primary"}
          />
        </div>
      ) : (
        <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
          <span className="h-1.5 w-1.5 rounded-full bg-warning" />
          No daily limit configured
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between border-t border-border pt-3">
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Risk
          </span>
          <span
            className={cn(
              "rounded px-1.5 py-0.5 text-[10px] font-bold tabular-nums",
              risk.tone === "success" && "bg-success/15 text-success",
              risk.tone === "warning" && "bg-warning/15 text-warning",
              risk.tone === "destructive" && "bg-destructive/15 text-destructive"
            )}
            title={risk.reason}
          >
            {risk.level}
          </span>
        </div>
        <span className="inline-flex items-center gap-1 text-xs font-medium text-primary opacity-0 transition-opacity group-hover:opacity-100">
          Manage <ArrowRight className="h-3 w-3" />
        </span>
      </div>
    </Link>
  );
}

export function AgentCardSkeleton() {
  return (
    <div className="flex flex-col gap-4 rounded-xl border border-border bg-card p-4">
      <div className="flex items-start gap-3">
        <div className="h-10 w-10 animate-pulse rounded-lg bg-muted" />
        <div className="flex-1 space-y-2">
          <div className="h-3.5 w-2/3 animate-pulse rounded bg-muted" />
          <div className="h-3 w-1/3 animate-pulse rounded bg-muted" />
        </div>
        <div className="h-5 w-14 animate-pulse rounded-full bg-muted" />
      </div>
      <div className="h-7 w-28 animate-pulse rounded bg-muted" />
      <div className="h-4 w-full animate-pulse rounded bg-muted" />
      <div className="h-4 w-full animate-pulse rounded bg-muted" />
    </div>
  );
}

export const AGENT_STATUS_TONE_CHECK = AGENT_STATUS_TONES;