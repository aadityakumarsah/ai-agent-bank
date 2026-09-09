"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Clock,
  Loader2,
  Pause,
  Play,
  Plus,
  RefreshCw,
  Repeat,
  Trash2,
  TrendingUp,
} from "lucide-react";
import { useWalletConnection } from "@/components/wallet/wallet-context";
import { api } from "@/lib/api";
import type { DcaFrequency, DcaPlan } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Panel } from "@/components/ui/panel";
import { EmptyState } from "@/components/ui/empty-state";
import { useToast } from "@/components/ui/toast";
import {
  formatUsdc,
  formatDate,
  shortAddress,
  cn,
} from "@/lib/utils";

const FREQUENCIES: { value: DcaFrequency; label: string }[] = [
  { value: "hourly", label: "Hourly" },
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
];

export function DcaPanel({ agentId }: { agentId: number }) {
  const { address } = useWalletConnection();
  const { toast } = useToast();

  const [plans, setPlans] = useState<DcaPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  const [tokenMint, setTokenMint] = useState(
    "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm"
  );
  const [tokenSymbol, setTokenSymbol] = useState("USDC");
  const [amount, setAmount] = useState("5");
  const [frequency, setFrequency] = useState<DcaFrequency>("daily");
  const [expanded, setExpanded] = useState<number | null>(null);

  const load = useCallback(async () => {
    if (!address) return;
    setLoading(true);
    try {
      const plans = await api.listDcaPlans(address, agentId);
      setPlans(plans);
    } catch (e) {
      toast({
        type: "error",
        title: "Failed to load DCA plans",
        description: e instanceof Error ? e.message : "Try again.",
      });
    } finally {
      setLoading(false);
    }
  }, [address, agentId, toast]);

  useEffect(() => {
    void load();
  }, [load]);

  const create = async () => {
    if (!address) return;
    const amt = parseFloat(amount);
    if (!amt || amt <= 0) {
      toast({ type: "error", title: "Invalid amount", description: "Enter a positive amount." });
      return;
    }
    setCreating(true);
    try {
      await api.createDcaPlan(address, {
        agent_id: agentId,
        token_mint: tokenMint.trim(),
        token_symbol: tokenSymbol.trim() || "TOKEN",
        token_decimals: 9,
        amount_per_cycle: amt,
        frequency,
      });
      toast({
        type: "success",
        title: "DCA plan created",
        description: `The agent will buy ${tokenSymbol.trim() || "token"} every ${frequency}.`,
      });
      setAmount("5");
      await load();
    } catch (e) {
      toast({
        type: "error",
        title: "Unable to create plan",
        description: e instanceof Error ? e.message : "Try again.",
      });
    } finally {
      setCreating(false);
    }
  };

  const setStatus = async (plan: DcaPlan, status: DcaPlan["status"]) => {
    if (!address) return;
    try {
      await api.updateDcaPlanStatus(address, plan.id, status);
      toast({
        type: "success",
        title: `Plan ${status}`,
        description: `${plan.token_symbol} DCA plan is now ${status}.`,
      });
      await load();
    } catch (e) {
      toast({
        type: "error",
        title: "Status update failed",
        description: e instanceof Error ? e.message : "Try again.",
      });
    }
  };

  const toggleExpanded = (id: number) =>
    setExpanded((prev) => (prev === id ? null : id));

  return (
    <div className="flex flex-col gap-6">
      <Panel
        title="New DCA plan"
        description="Automatically spend a fixed USDC amount from the escrow on a recurring schedule. Each trade is policy-governed and recorded in the ledger."
      >
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Input
            id="dca-token-mint"
            label="Token mint"
            placeholder="SPL token mint to buy"
            value={tokenMint}
            onChange={(e) => setTokenMint(e.target.value)}
          />
          <Input
            id="dca-token-symbol"
            label="Token symbol"
            placeholder="SOL"
            value={tokenSymbol}
            onChange={(e) => setTokenSymbol(e.target.value)}
          />
          <Input
            id="dca-amount"
            label="Amount per cycle (USDC)"
            type="number"
            min="0"
            prefix="$"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
          />
          <div>
            <div className="mb-1.5 text-xs font-medium text-muted-foreground">
              Frequency
            </div>
            <div className="flex overflow-hidden rounded-lg border border-border">
              {FREQUENCIES.map((f) => (
                <button
                  key={f.value}
                  type="button"
                  onClick={() => setFrequency(f.value)}
                  className={cn(
                    "flex-1 px-3 py-2 text-xs font-medium transition-colors",
                    frequency === f.value
                      ? "bg-primary text-primary-foreground"
                      : "bg-background text-muted-foreground hover:text-foreground"
                  )}
                >
                  {f.label}
                </button>
              ))}
            </div>
            {frequency === "hourly" && (
              <p className="mt-1 text-[11px] text-muted-foreground">
                Aggressive: 24 buys/day. Daily/monthly policy caps still apply.
              </p>
            )}
          </div>
        </div>
        <div className="mt-4">
          <Button onClick={create} disabled={creating || !(parseFloat(amount) > 0)}>
            {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            Create DCA plan
          </Button>
        </div>
      </Panel>

      <Panel
        title="DCA plans"
        description="Recurring buys for this agent"
        action={
          <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => void load()}>
            <RefreshCw className="h-3.5 w-3.5" /> Refresh
          </Button>
        }
      >
        {loading ? (
          <div className="space-y-3">
            {[0, 1].map((i) => (
              <div key={i} className="h-20 animate-pulse rounded-lg border border-border bg-muted/40" />
            ))}
          </div>
        ) : plans.length === 0 ? (
          <EmptyState
            icon={Repeat}
            title="No DCA plans"
            description="Create your first recurring buy above."
          />
        ) : (
          <div className="flex flex-col divide-y divide-border/60">
            {plans.map((plan) => (
              <PlanRow
                key={plan.id}
                plan={plan}
                expanded={expanded === plan.id}
                onToggle={() => toggleExpanded(plan.id)}
                onStatus={(s) => void setStatus(plan, s)}
              />
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}

function PlanRow({
  plan,
  expanded,
  onToggle,
  onStatus,
}: {
  plan: DcaPlan;
  expanded: boolean;
  onToggle: () => void;
  onStatus: (s: DcaPlan["status"]) => void;
}) {
  const [execs, setExecs] = useState<Awaited<ReturnType<typeof api.listDcaExecutions>>>([]);
  const { address } = useWalletConnection();

  useEffect(() => {
    if (expanded && address) {
      api
        .listDcaExecutions(address, plan.id)
        .then(setExecs)
        .catch(() => setExecs([]));
    }
  }, [expanded, address, plan.id]);

  const runs = plan.runs_completed ?? 0;
  const invested = plan.total_invested ?? 0;

  return (
    <div className="px-4 py-3 sm:px-5">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-secondary text-primary">
          <TrendingUp className="h-4 w-4" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-foreground">{plan.token_symbol || "Token"}</span>
            <FrequencyBadge frequency={plan.frequency} />
            <StatusBadge status={plan.status} />
          </div>
          <div className="mt-0.5 truncate font-mono text-[11px] text-muted-foreground">
            {shortAddress(plan.token_mint, 8)}
            {plan.next_run_at ? ` · next ${formatDate(plan.next_run_at)}` : ""}
          </div>
        </div>
        <div className="text-right">
          <div className="text-sm font-bold tabular-nums text-foreground">{formatUsdc(plan.amount_per_cycle)}</div>
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground">per cycle</div>
        </div>
        <div className="text-right">
          <div className="text-sm font-semibold tabular-nums text-foreground">{runs}</div>
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground">buys · {formatUsdc(invested)}</div>
        </div>
        <div className="flex items-center gap-1.5">
          {plan.status === "active" ? (
            <Button variant="outline" size="sm" className="h-8 w-8 p-0" title="Pause" onClick={() => onStatus("paused")}>
              <Pause className="h-3.5 w-3.5" />
            </Button>
          ) : plan.status === "paused" ? (
            <Button variant="outline" size="sm" className="h-8 w-8 p-0" title="Resume" onClick={() => onStatus("active")}>
              <Play className="h-3.5 w-3.5" />
            </Button>
          ) : null}
          {plan.status === "active" || plan.status === "paused" ? (
            <Button variant="outline" size="sm" className="h-8 w-8 p-0" title="Cancel plan" onClick={() => onStatus("cancelled")}>
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          ) : null}
          <Button variant="ghost" size="sm" className="h-8 px-2 text-xs" onClick={onToggle}>
            {expanded ? "Hide" : "History"}
          </Button>
        </div>
      </div>

      {expanded && (
        <div className="mt-3 rounded-lg border border-border bg-background/40">
          {execs.length === 0 ? (
            <div className="px-3 py-3 text-xs text-muted-foreground">No executions yet.</div>
          ) : (
            <div className="flex flex-col divide-y divide-border/40">
              {execs.map((x) => (
                <div key={x.id} className="flex items-center justify-between gap-3 px-3 py-2 text-xs">
                  <div className="flex items-center gap-2 min-w-0">
                    <Clock className="h-3 w-3 shrink-0 text-muted-foreground" />
                    <span className="text-muted-foreground">{x.created_at ? formatDate(x.created_at) : "—"}</span>
                    {x.out_amount != null && (
                      <span className="font-medium text-foreground">
                        +{x.out_amount} {x.out_unit || "token"}
                      </span>
                    )}
                  </div>
                  <ReasonBadge status={x.status} error={x.error} />
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function FrequencyBadge({ frequency }: { frequency: DcaFrequency }) {
  return (
    <span className="rounded bg-secondary px-1.5 py-0.5 text-[10px] font-semibold text-foreground">
      {frequency}
    </span>
  );
}

function StatusBadge({ status }: { status: DcaPlan["status"] }) {
  const tone =
    status === "active"
      ? "bg-success/15 text-success"
      : status === "paused"
        ? "bg-warning/15 text-warning"
        : "bg-muted text-muted-foreground";
  return <span className={cn("rounded px-1.5 py-0.5 text-[10px] font-bold", tone)}>{status}</span>;
}

function ReasonBadge({ status, error }: { status: string; error: string | null }) {
  if (status === "completed")
    return <span className="rounded bg-success/15 px-1.5 py-0.5 text-[10px] font-bold text-success">EXECUTED</span>;
  if (status === "skipped")
    return (
      <span className="rounded bg-warning/15 px-1.5 py-0.5 text-[10px] font-bold text-warning" title={error ?? undefined}>
        SKIPPED
      </span>
    );
  if (status === "failed")
    return (
      <span className="rounded bg-destructive/15 px-1.5 py-0.5 text-[10px] font-bold text-destructive" title={error ?? undefined}>
        FAILED
      </span>
    );
  return <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-bold text-muted-foreground">{status}</span>;
}