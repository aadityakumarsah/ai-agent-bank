import { Badge } from "@/components/ui/badge";
import {
  TX_STATUS_LABELS,
  TX_STATUS_TONES,
  AGENT_STATUS_LABELS,
  AGENT_STATUS_TONES,
} from "@/lib/types";
import { cn } from "@/lib/utils";

function StatusDot({ tone, className }: { tone: string; className?: string }) {
  const tones: Record<string, string> = {
    success: "bg-success",
    warning: "bg-warning",
    destructive: "bg-destructive",
    info: "bg-info",
    neutral: "bg-muted-foreground",
  };
  return (
    <span className={cn("inline-block h-1.5 w-1.5 shrink-0 rounded-full", tones[tone] ?? tones.neutral, className)} />
  );
}

function TransactionStatusBadge({ status }: { status: string }) {
  const tone = TX_STATUS_TONES[status] ?? "neutral";
  const variant = tone === "success" ? "success" : tone === "destructive" ? "destructive" : tone === "warning" ? "warning" : tone === "info" ? "info" : "neutral";
  return (
    <Badge variant={variant} className="gap-1.5">
      <StatusDot tone={tone} />
      {TX_STATUS_LABELS[status] ?? status}
    </Badge>
  );
}

function AgentStatusBadge({ status, uppercase }: { status: string; uppercase?: boolean }) {
  const tone = AGENT_STATUS_TONES[status] ?? "neutral";
  const variant = tone === "success" ? "success" : tone === "warning" ? "warning" : tone === "destructive" ? "destructive" : "neutral";
  return (
    <Badge variant={variant} className="gap-1.5">
      <StatusDot tone={tone} />
      <span className={cn(uppercase && "font-bold tracking-wide")}>
        {uppercase ? AGENT_STATUS_LABELS[status] ?? status.toUpperCase() : status}
      </span>
    </Badge>
  );
}

export { TransactionStatusBadge, AgentStatusBadge, StatusDot };