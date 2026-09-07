"use client";

import { Bot, Check, X, Clock, Timer, Inbox } from "lucide-react";
import type { ApprovalRequest } from "@/lib/types";
import { CATEGORY_LABELS } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { formatUsdc, shortAddress } from "@/lib/utils";
import { useCountdown, formatCountdown } from "@/hooks/use-countdown";
import { cn } from "@/lib/utils";

export function ApprovalCard({
  request,
  onApprove,
  onReject,
}: {
  request: ApprovalRequest;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
}) {
  const { remaining, expired } = useCountdown(request.expiresAt);
  const urgent = !expired && remaining < 2 * 60 * 1000;
  const decided = request.status !== "pending";

  return (
    <div
      className={cn(
        "flex flex-col gap-4 rounded-xl border bg-card p-4 transition-colors",
        expired ? "border-border opacity-60" : "border-border",
        decided && request.status === "approved" && "border-success/30",
        decided && request.status === "rejected" && "border-destructive/30",
        !decided && !expired && "hover:border-primary/30"
      )}
    >
      <div className="flex items-start gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-secondary text-primary">
          <Bot className="h-4.5 w-4.5" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-sm font-semibold text-foreground">{request.agentName}</span>
            {request.simulated && (
              <span className="rounded border border-warning/30 bg-warning/10 px-1 py-px text-[9px] font-bold tracking-wide text-warning">
                SIMULATED
              </span>
            )}
            {request.category && (
              <span className="rounded border border-border bg-card px-1.5 py-px text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                {CATEGORY_LABELS[request.category] ?? request.category}
              </span>
            )}
          </div>
          <p className="mt-0.5 text-xs text-muted-foreground">
            wants to spend{" "}
            <span className="font-semibold tabular-nums text-foreground">
              {formatUsdc(request.amount)} {request.currency}
            </span>
          </p>
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <div className="rounded-lg border border-border bg-background/40 px-3 py-2">
          <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Reason
          </div>
          <div className="mt-0.5 text-sm text-foreground">{request.reason}</div>
        </div>
        <div className="rounded-lg border border-border bg-background/40 px-3 py-2">
          <div className="flex items-start gap-1.5">
            <Inbox className="mt-0.5 h-3.5 w-3.5 shrink-0 text-info" />
            <span className="text-xs text-muted-foreground">{request.policyNote}</span>
          </div>
        </div>
        {(request.recipientName || request.recipient) && (
          <div className="rounded-lg border border-border bg-background/40 px-3 py-2">
            <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
              Recipient
            </div>
            <div className="mt-0.5 text-xs text-foreground">
              {request.recipientName ?? shortAddress(request.recipient, 8)}
              {request.recipientName && request.recipient && (
                <span className="ml-2 font-mono text-[10px] text-muted-foreground">
                  {shortAddress(request.recipient, 5)}
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="mt-auto flex items-center justify-between gap-3 border-t border-border pt-3">
        <div
          className={cn(
            "inline-flex items-center gap-1.5 text-xs font-medium tabular-nums",
            decided
              ? request.status === "approved"
                ? "text-success"
                : "text-destructive"
              : expired
                ? "text-muted-foreground"
                : urgent
                  ? "text-warning"
                  : "text-muted-foreground"
          )}
        >
          {decided ? (
            <>
              {request.status === "approved" ? <Check className="h-3.5 w-3.5" /> : <X className="h-3.5 w-3.5" />}
              {request.status === "approved" ? "Approved" : "Rejected"}
            </>
          ) : expired ? (
            <>
              <Timer className="h-3.5 w-3.5" /> Expired
            </>
          ) : (
            <>
              <Clock className={cn("h-3.5 w-3.5", urgent && "animate-pulse")} />
              Expires {formatCountdown(remaining)}
            </>
          )}
        </div>
        {!decided && !expired && (
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="h-8 text-xs"
              onClick={() => onReject(request.id)}
            >
              <X className="h-3.5 w-3.5" />
              Reject
            </Button>
            <Button variant="success" size="sm" className="h-8 text-xs" onClick={() => onApprove(request.id)}>
              <Check className="h-3.5 w-3.5" />
              Approve
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}