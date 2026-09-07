"use client";

import {
  Activity,
  ShieldCheck,
  ShieldAlert,
  BadgeCheck,
  XCircle,
  Bot,
  Wallet,
  Shield,
  Play,
  Inbox,
  PauseCircle,
  HandCoins,
} from "lucide-react";
import type { ActivityEvent } from "@/lib/types";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { formatUsdc, formatTime, explorerTxUrl, shortAddress } from "@/lib/utils";
import { cn } from "@/lib/utils";
import { isSimulatedSignature } from "@/lib/solana";

const EVENT_META: Record<
  string,
  { icon: React.ElementType; tone: string }
> = {
  request: { icon: HandCoins, tone: "info" },
  policy_allowed: { icon: ShieldCheck, tone: "success" },
  policy_blocked: { icon: ShieldAlert, tone: "destructive" },
  payment_completed: { icon: BadgeCheck, tone: "success" },
  payment_failed: { icon: XCircle, tone: "destructive" },
  agent_created: { icon: Bot, tone: "primary" },
  agent_funded: { icon: Wallet, tone: "success" },
  policy_updated: { icon: Shield, tone: "info" },
  task_started: { icon: Play, tone: "info" },
  approval_required: { icon: Inbox, tone: "warning" },
  agent_paused: { icon: PauseCircle, tone: "warning" },
  system: { icon: Activity, tone: "neutral" },
};

const toneClasses: Record<string, string> = {
  primary: "border-primary/30 bg-primary/10 text-primary",
  success: "border-success/30 bg-success/10 text-success",
  warning: "border-warning/30 bg-warning/10 text-warning",
  destructive: "border-destructive/30 bg-destructive/10 text-destructive",
  info: "border-info/30 bg-info/10 text-info",
  neutral: "border-border bg-muted text-muted-foreground",
};

function EventIcon({ e }: { e: ActivityEvent }) {
  const meta = EVENT_META[e.type] ?? EVENT_META.system;
  const Icon = meta.icon;
  return (
    <span
      className={cn(
        "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border",
        toneClasses[meta.tone] ?? toneClasses.neutral
      )}
    >
      <Icon className="h-4 w-4" />
    </span>
  );
}

function ChecksRow({ e }: { e: ActivityEvent }) {
  if (!e.checks?.length) return null;
  return (
    <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
      {e.checks.map((c, i) => (
        <span
          key={i}
          className={cn(
            "inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[10px] font-medium",
            c.passed
              ? "border-success/25 bg-success/5 text-success"
              : "border-destructive/25 bg-destructive/5 text-destructive"
          )}
        >
          {c.passed ? "✓" : "✕"} {c.name}
        </span>
      ))}
    </div>
  );
}

export function ActivityFeed({
  events,
  live,
  toggleLive,
  onClearSimulated,
  compact,
  emptyTitle = "No activity yet",
  emptyDescription = "Agent events will appear here in real time.",
  network = "devnet",
}: {
  events: ActivityEvent[];
  live?: boolean;
  toggleLive?: () => void;
  onClearSimulated?: () => void;
  compact?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  network?: "devnet" | "mainnet-beta";
}) {
  if (events.length === 0) {
    return <EmptyState icon={Activity} title={emptyTitle} description={emptyDescription} />;
  }

  return (
    <div className="relative">
      <div className="absolute bottom-2 left-[15px] top-2 w-px bg-border" aria-hidden />
      <ul className="flex flex-col">
        {events.slice(0, compact ? 12 : 80).map((e) => {
          const isSim = e.simulated;
          return (
            <li key={e.id} className="relative flex gap-3.5 pb-4 last:pb-0 animate-fade-up">
              <div className="relative z-10">
                <EventIcon e={e} />
              </div>
              <div className="min-w-0 flex-1 pt-1">
                <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                  <span className="text-sm font-medium leading-none text-foreground">
                    {e.agentName}
                  </span>
                  {isSim && (
                    <span className="rounded border border-warning/30 bg-warning/10 px-1 py-px text-[9px] font-bold tracking-wide text-warning">
                      SIM
                    </span>
                  )}
                  {e.label && (
                    <span className="text-xs text-muted-foreground">{e.label}</span>
                  )}
                  {e.amount !== undefined && (
                    <span className="rounded bg-secondary px-1.5 py-0.5 text-[11px] font-semibold tabular-nums text-foreground">
                      {formatUsdc(e.amount)}{" "}
                      <span className="font-normal text-muted-foreground">{e.currency}</span>
                    </span>
                  )}
                </div>
                {e.detail && (
                  <div
                    className={cn(
                      "mt-1 text-xs leading-snug",
                      e.type === "policy_blocked"
                        ? "font-semibold text-destructive"
                        : e.type === "policy_allowed"
                          ? "font-medium text-success"
                          : "text-muted-foreground"
                    )}
                  >
                    {e.detail}
                  </div>
                )}
                <ChecksRow e={e} />
                {e.signature &&
                  (isSimulatedSignature(e.signature) ? (
                    <span className="mt-1.5 inline-flex items-center gap-1 rounded border border-warning/25 bg-warning/5 px-1 py-px font-mono text-[10px] text-warning" title="MOCK MODE — simulated, nothing on-chain">
                      {shortAddress(e.signature, 8)}
                    </span>
                  ) : (
                    <a
                      href={explorerTxUrl(e.signature, network)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-1.5 inline-block font-mono text-[10px] text-info hover:text-foreground"
                    >
                      {shortAddress(e.signature, 8)}
                    </a>
                  ))}
              </div>
              <div className="shrink-0 pt-1 font-mono text-[10px] tabular-nums text-muted-foreground">
                {formatTime(new Date(e.timestamp).toISOString())}
              </div>
            </li>
          );
        })}
      </ul>
      {live !== undefined && (
        <div className="mt-3 flex items-center justify-between gap-3 border-t border-border pt-3">
          <button
            onClick={toggleLive}
            className={cn(
              "inline-flex items-center gap-2 text-xs font-semibold transition-colors",
              live ? "text-success" : "text-muted-foreground hover:text-foreground"
            )}
          >
            <span className="relative flex h-2 w-2">
              {live && (
                <span className="absolute inline-flex h-full w-full rounded-full bg-success opacity-50 animate-ping" />
              )}
              <span
                className={cn(
                  "relative inline-flex h-2 w-2 rounded-full",
                  live ? "bg-success" : "bg-muted-foreground"
                )}
              />
            </span>
            {live ? "LIVE" : "PAUSED"}
          </button>
          {onClearSimulated && (
            <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={onClearSimulated}>
              Clear simulated
            </Button>
          )}
        </div>
      )}
    </div>
  );
}

export function ActivityFeedSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div className="flex flex-col gap-4">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-start gap-3">
          <Skeleton className="h-8 w-8 rounded-lg" />
          <div className="flex-1 space-y-2 pt-1">
            <Skeleton className="h-3 w-1/3" />
            <Skeleton className="h-3 w-1/2" />
          </div>
          <Skeleton className="h-3 w-14" />
        </div>
      ))}
    </div>
  );
}