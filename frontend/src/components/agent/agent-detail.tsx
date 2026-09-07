"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Bot,
  Coins,
  Copy,
  Check,
  PowerOff,
  Power,
  Trash2,
  Loader2,
  Wallet,
  TrendingUp,
  ExternalLink,
  ShieldCheck,
  ArrowDownToLine,
} from "lucide-react";
import { useWalletConnection } from "@/components/wallet/wallet-context";
import { useConfigStatus } from "@/hooks/use-config-status";
import { api } from "@/lib/api";
import type { Agent, TaskRunResult, Transaction } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog } from "@/components/ui/dialog";
import { StatCard } from "@/components/ui/stat-card";
import { Panel } from "@/components/ui/panel";
import { Tabs } from "@/components/ui/tabs";
import { ProgressRing } from "@/components/ui/progress-ring";
import { AgentStatusBadge, TransactionStatusBadge } from "@/components/ui/status-badge";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import { EmptyState } from "@/components/ui/empty-state";
import { useToast } from "@/components/ui/toast";
import { formatUsdc, formatDate, shortAddress, percentOf, explorerAddressUrl, cn } from "@/lib/utils";
import { spentTodayForAgent, riskLevel } from "@/lib/risk";
import { PolicyPanel } from "@/components/agent/policy-panel";
import { TaskRunner } from "@/components/agent/task-runner";
import { TransactionTable } from "@/components/transactions/transaction-table";
import { ActivityFeed } from "@/components/activity/activity-feed";
import { transactionToActivity } from "@/lib/activity";
import { signAndSendUsdcTransfer, explorerUrlForSignature } from "@/lib/solana";

type TabId = "overview" | "wallet" | "policy" | "tasks" | "transactions" | "activity";

const TABS: { value: TabId; label: string }[] = [
  { value: "overview", label: "Overview" },
  { value: "wallet", label: "Wallet" },
  { value: "policy", label: "Policy" },
  { value: "tasks", label: "Tasks" },
  { value: "transactions", label: "Transactions" },
  { value: "activity", label: "Activity" },
];

export function AgentDetail({ agentId }: { agentId: number }) {
  const { address, isDemo } = useWalletConnection();
  const { status } = useConfigStatus();
  const router = useRouter();
  const { toast } = useToast();

  const [agent, setAgent] = useState<Agent | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [runs, setRuns] = useState<TaskRunResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [tab, setTab] = useState<TabId>("overview");
  const [dealDialog, setDealDialog] = useState<"suspend" | "resume" | "kill" | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!address) return;
    setLoading(true);
    setError(null);
    try {
      const [a, txs, rs] = await Promise.all([
        api.getAgent(address, agentId),
        api.listTransactions(address),
        api.listRuns(address, agentId),
      ]);
      setAgent(a);
      setTransactions(txs.filter((t) => t.agent_id === agentId));
      setRuns(rs);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load agent");
    } finally {
      setLoading(false);
    }
  }, [address, agentId]);

  useEffect(() => {
    if (address) void load();
  }, [address, load]);

  useEffect(() => {
    const q = new URLSearchParams(window.location.search).get("tab");
    if (q && TABS.some((t) => t.value === q)) setTab(q as TabId);
  }, []);

  const action = async (
    fn: () => Promise<void>,
    successTitle: string,
    successDescription: string
  ) => {
    setBusy(true);
    setDealDialog(null);
    try {
      await fn();
      toast({ type: "success", title: successTitle, description: successDescription });
    } catch (e) {
      toast({ type: "error", title: "Action failed", description: e instanceof Error ? e.message : "Try again." });
    } finally {
      setBusy(false);
    }
  };

  const applyPolicy = async (policy: Parameters<typeof api.setPolicy>[2]) => {
    if (!address) return;
    await api.setPolicy(address, agentId, policy);
    await load();
    toast({
      type: "success",
      title: "Policy applied",
      description: "The policy engine will enforce these rules from now on.",
    });
  };

  if (loading && !agent) {
    return <AgentDetailSkeleton />;
  }

  if (!agent) {
    return (
      <div className="flex flex-col gap-4">
        {error && <ErrorState description={error} onRetry={() => void load()} />}
        {!error && (
          <div className="py-20 text-center text-muted-foreground">Agent not found.</div>
        )}
        <Button variant="ghost" size="sm" className="-ml-2 self-start" onClick={() => router.push("/agents")}>
          <ArrowLeft className="h-4 w-4" /> Back to agents
        </Button>
      </div>
    );
  }

  const spentToday = spentTodayForAgent(transactions, agent.id);
  const dailyLimit = agent.policies?.max_per_day ?? 0;
  const remaining = Math.max(0, dailyLimit - spentToday);
  const risk = riskLevel(agent);

  return (
    <div className="flex flex-col gap-6">
      <Button variant="ghost" size="sm" className="-ml-2 self-start" onClick={() => router.push("/agents")}>
        <ArrowLeft className="h-4 w-4" /> Agents
      </Button>

      {error && (
        <div className="flex items-center gap-2 text-sm text-destructive">
          <span>{error}</span>
          <Button variant="outline" size="sm" onClick={() => void load()}>Retry</Button>
        </div>
      )}

      {/* Hero */}
      <div className="flex flex-col gap-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex items-center gap-4">
            <div className="relative flex h-14 w-14 shrink-0 items-center justify-center rounded-xl bg-secondary text-primary">
              <Bot className="h-7 w-7" />
              <span className={cn("absolute -bottom-0.5 -right-0.5 h-3.5 w-3.5 rounded-full border-2 border-background", agent.status === "active" ? "bg-success" : agent.status === "suspended" ? "bg-warning" : "bg-destructive")} />
            </div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-2xl font-bold tracking-tight text-foreground">{agent.name}</h1>
                <AgentStatusBadge status={agent.status} />
                <span
                  className={cn(
                    "rounded px-1.5 py-0.5 text-[10px] font-bold tracking-wide",
                    risk.tone === "success" && "bg-success/15 text-success",
                    risk.tone === "warning" && "bg-warning/15 text-warning",
                    risk.tone === "destructive" && "bg-destructive/15 text-destructive"
                  )}
                  title={risk.reason}
                >
                  RISK: {risk.level}
                </span>
              </div>
              <p className="mt-1 max-w-xl truncate text-sm text-muted-foreground">
                {agent.description || "No description"}
              </p>
              <div className="mt-1.5 flex items-center gap-1.5 text-xs text-muted-foreground">
                <span>Created {formatDate(agent.created_at)}</span>
                <span>·</span>
                <span
                  className={cn(
                    "inline-flex items-center gap-1",
                    status?.payment_mode === "mock" ? "text-warning" : "text-success"
                  )}
                >
                  <ShieldCheck className="h-3 w-3" />
                  {status?.payment_mode === "mock" ? "DEMO MODE" : "SOLANA DEVNET"}
                </span>
              </div>
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            <Button
              variant="outline"
              onClick={() => setTab("wallet")}
              className="sm:hidden"
            >
              <Coins className="h-4 w-4" /> Fund
            </Button>
            {agent.status === "active" ? (
              <Button variant="warning" onClick={() => setDealDialog("suspend")}>
                <PowerOff className="h-4 w-4" /> Pause Agent
              </Button>
            ) : agent.status === "suspended" ? (
              <Button variant="success" onClick={() => setDealDialog("resume")}>
                <Power className="h-4 w-4" /> Resume Agent
              </Button>
            ) : null}
            <Button variant="destructive" onClick={() => setDealDialog("kill")}>
              <Trash2 className="h-4 w-4" /> Kill Agent
            </Button>
          </div>
        </div>

        <div className="flex items-center gap-3 rounded-xl border border-border bg-card px-4 py-3">
          <div className="text-sm font-semibold tabular-nums text-success">{formatUsdc(agent.balance)}</div>
          <span className="text-xs text-muted-foreground">USDC available</span>
          <div className="ml-auto flex items-center gap-1.5">
            <Wallet className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-xs text-muted-foreground">Escrow</span>
            <span className="font-mono text-xs text-foreground">
              {shortAddress(agent.escrow_address, 6)}
            </span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <Tabs
        tabs={TABS.map((t) => ({
          ...t,
          count: t.value === "transactions" ? transactions.length : undefined,
        }))}
        value={tab}
        onChange={setTab}
      />

      {tab === "overview" && (
        <OverviewTab
          agent={agent}
          transactions={transactions}
          spentToday={spentToday}
          onFund={() => setTab("wallet")}
        />
      )}
      {tab === "wallet" && (
        <WalletTab
          agent={agent}
          address={address!}
          transactions={transactions}
          paymentMode={status?.payment_mode ?? "mock"}
          network={status?.solana_network ?? "devnet"}
          isDemoWallet={isDemo}
          onFunded={(updated) => setAgent(updated)}
          loading={loading}
        />
      )}
      {tab === "policy" && <PolicyPanel current={agent.policies} onApply={applyPolicy} />}
      {tab === "tasks" && (
        <TasksTab agent={agent} address={address!} runs={runs} onTransaction={() => void load()} />
      )}
      {tab === "transactions" && (
        <Panel title="Transactions" description="Every payment attempt for this agent" bodyClassName="p-3 sm:p-4">
          <TransactionTable transactions={transactions} hideAgent />
        </Panel>
      )}
      {tab === "activity" && (
        <Panel title={`${agent.name} activity`} description="Policy decisions and payments" bodyClassName="p-4 sm:p-5">
          <AgentActivity transactions={transactions} agentName={agent.name} />
        </Panel>
      )}

      {/* Lifecycle dialogs */}
      <Dialog
        open={dealDialog === "suspend"}
        onClose={() => setDealDialog(null)}
        title={`Pause ${agent.name}?`}
        description="The agent will be suspended and unable to transact until you resume it."
        footer={
          <>
            <Button variant="outline" onClick={() => setDealDialog(null)}>Cancel</Button>
            <Button
              variant="warning"
              disabled={busy}
              onClick={() => action(async () => {
                const updated = await api.updateAgentStatus(address!, agentId, "suspended");
                setAgent(updated);
              }, "Agent paused", `${agent.name} can no longer transact.`)}
            >
              {busy && <Loader2 className="h-4 w-4 animate-spin" />}
              Pause Agent
            </Button>
          </>
        }
      >
        <p className="text-sm text-muted-foreground">
          Paused agents keep their balance and policy. Tasks currently in flight will be
          halted at the next tool boundary.
        </p>
      </Dialog>

      <Dialog
        open={dealDialog === "resume"}
        onClose={() => setDealDialog(null)}
        title={`Resume ${agent.name}?`}
        description="Bring the agent back online so it can accept tasks again."
        footer={
          <>
            <Button variant="outline" onClick={() => setDealDialog(null)}>Cancel</Button>
            <Button
              variant="success"
              disabled={busy}
              onClick={() => action(async () => {
                const updated = await api.updateAgentStatus(address!, agentId, "active");
                setAgent(updated);
              }, "Agent resumed", `${agent.name} is active again.`)}
            >
              {busy && <Loader2 className="h-4 w-4 animate-spin" />}
              Resume Agent
            </Button>
          </>
        }
      />

      <Dialog
        open={dealDialog === "kill"}
        onClose={() => setDealDialog(null)}
        title={`Kill ${agent.name}?`}
        description="This permanently revokes the agent. It can never transact again."
        footer={
          <>
            <Button variant="outline" onClick={() => setDealDialog(null)}>Cancel</Button>
            <Button
              variant="destructive"
              disabled={busy}
              onClick={() => action(async () => {
                await api.killAgent(address!, agentId);
                router.push("/agents");
              }, "Agent killed", `${agent.name} was permanently revoked.`)}
            >
              {busy && <Loader2 className="h-4 w-4 animate-spin" />}
              Kill Agent
            </Button>
          </>
        }
      >
        <div className="rounded-lg border border-destructive/25 bg-destructive/5 px-3 py-2.5 text-sm text-destructive">
          <p className="flex items-center gap-1.5">
            <Trash2 className="h-4 w-4" />
            The humans are the final authority. This cannot be undone.
          </p>
        </div>
      </Dialog>
    </div>
  );
}

// ---------------------------------------------------------------- tabs

function OverviewTab({
  agent,
  transactions,
  spentToday,
  onFund,
}: {
  agent: Agent;
  transactions: Transaction[];
  spentToday: number;
  onFund: () => void;
}) {
  const dailyLimit = agent.policies?.max_per_day ?? 0;
  const remaining = Math.max(0, dailyLimit - spentToday);
  const pct = percentOf(spentToday, dailyLimit);
  const risk = riskLevel(agent);
  const recentTxs = useMemo(() => transactions.slice(0, 6), [transactions]);
  const activityEvents = useMemo(
    () =>
      transactions
        .map((t) => transactionToActivity(t, agent.name))
        .filter((e): e is NonNullable<typeof e> => e !== null),
    [transactions, agent.name]
  );

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Balance" value={formatUsdc(agent.balance)} icon={Wallet} tone="success" hint="USDC in escrow" />
        <StatCard label="Total spent" value={formatUsdc(agent.total_spent)} icon={TrendingUp} hint="Lifetime" />
        <StatCard label="Spent today" value={formatUsdc(spentToday)} icon={Coins} tone="primary" hint={dailyLimit ? `${Math.round(pct)}% of daily limit` : "No daily limit"} />
        <StatCard label="Risk level" value={risk.level} icon={ShieldCheck} tone={risk.tone === "success" ? "success" : risk.tone === "warning" ? "warning" : "destructive"} hint={risk.reason} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Panel title="Daily spending" description="Today's utilization against the policy's daily limit">
          {dailyLimit > 0 ? (
            <div className="flex items-center gap-6">
              <ProgressRing value={pct} size={128} stroke={11} tone={pct >= 85 ? "destructive" : pct >= 60 ? "warning" : "primary"}>
                <div className="text-center">
                  <div className="text-xl font-bold tabular-nums text-foreground">{Math.round(pct)}%</div>
                  <div className="text-[9px] uppercase tracking-wider text-muted-foreground">used</div>
                </div>
              </ProgressRing>
              <div className="w-full min-w-0 space-y-1.5">
                <SpendRow label="Daily limit" value={formatUsdc(dailyLimit)} />
                <SpendRow
                  label="Monthly limit"
                  value={
                    agent.policies?.max_per_month != null
                      ? formatUsdc(agent.policies.max_per_month)
                      : "Unlimited"
                  }
                />
                <SpendRow label="Spent" value={formatUsdc(spentToday)} />
                <SpendRow label="Remaining" value={formatUsdc(remaining)} accent={pct >= 85 ? "text-warning" : "text-success"} />
                <Progress value={pct} tone={pct >= 85 ? "destructive" : pct >= 60 ? "warning" : "primary"} className="mt-2" />
              </div>
            </div>
          ) : (
            <EmptyState
              icon={ShieldCheck}
              title="No daily limit"
              description="Set a policy to bound daily spending."
            />
          )}
        </Panel>

        <Panel
          title="Recent activity"
          description="Policy decisions and payments"
          bodyClassName="p-4 sm:p-5"
        >
          <ActivityFeed events={activityEvents} compact />
        </Panel>
      </div>

      <Panel
        title="Recent transactions"
        description={`${transactions.length} total for this agent`}
        bodyClassName="p-3 sm:p-4"
        action={
          <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={onFund}>
            <Coins className="h-3.5 w-3.5" /> Fund
          </Button>
        }
      >
        {recentTxs.length ? (
          <TransactionTable transactions={recentTxs} hideAgent />
        ) : (
          <EmptyState
            icon={Wallet}
            title="No transactions yet"
            description="Give the agent a task to see the policy engine in action."
          />
        )}
      </Panel>
    </div>
  );
}

function SpendRow({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div className="flex items-center justify-between text-xs">
      <span className="text-muted-foreground">{label}</span>
      <span className={cn("font-semibold tabular-nums text-foreground", accent)}>{value}</span>
    </div>
  );
}

// ---------------------------------------------------------------- wallet

function WalletTab({
  agent,
  address,
  transactions,
  paymentMode,
  network,
  isDemoWallet,
  onFunded,
  loading,
}: {
  agent: Agent;
  address: string;
  transactions: Transaction[];
  paymentMode: "mock" | "real";
  network: string;
  isDemoWallet: boolean;
  onFunded: (a: Agent) => void;
  loading: boolean;
}) {
  const { toast } = useToast();
  const [amount, setAmount] = useState("100");
  const [funding, setFunding] = useState(false);
  const [copied, setCopied] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [lastTx, setLastTx] = useState<{ kind: "mock" | "real"; signature: string } | null>(null);

  const fund = async () => {
    const amt = parseFloat(amount);
    if (!amt || amt <= 0) return;
    setFunding(true);
    setConfirmed(false);
    setLastTx(null);

    // REAL MODE — the user's wallet signs a real USDC transfer into the escrow.
    if (paymentMode === "real" && !isDemoWallet) {
      try {
        const res = await api.fundAgent(address, agent.id, amt);
        if (res.mode !== "solana" || !res.payment_request) {
          throw new Error("Backend did not return a payment request.");
        }
        const req = res.payment_request;
        const signature = await signAndSendUsdcTransfer({
          from: address,
          to: req.to_address,
          amount: amt,
          mint: req.mint,
        });
        const updated = await api.confirmFund(address, agent.id, amt, signature);
        onFunded(updated);
        setConfirmed(true);
        setLastTx({ kind: "real", signature });
        toast({
          type: "success",
          title: `Funded ${agent.name}`,
          description: `${formatUsdc(amt)} USDC confirmed in escrow on Solana.`,
        });
      } catch (e) {
        toast({ type: "error", title: "Funding failed", description: e instanceof Error ? e.message : "Try again." });
      } finally {
        setFunding(false);
      }
      return;
    }

    if (paymentMode === "real" && isDemoWallet) {
      setFunding(false);
      toast({
        type: "warning",
        title: "REAL MODE needs a real wallet",
        description: "Connect Phantom (or another Solana wallet) to sign real USDC transfers.",
      });
      return;
    }

    // MOCK MODE — simulated funding. Never presented as a real transaction.
    try {
      const res = await api.fundAgent(address, agent.id, amt);
      if (res.mode !== "mock" || !res.agent) {
        throw new Error("Unexpected backend response.");
      }
      onFunded(res.agent);
      setConfirmed(true);
      setLastTx({ kind: "mock", signature: res.tx_hash });
      toast({
        type: "success",
        title: `Funded ${agent.name} (SIMULATED)`,
        description: `${formatUsdc(amt)} USDC added to escrow in MOCK MODE.`,
      });
    } catch (e) {
      toast({ type: "error", title: "Funding failed", description: e instanceof Error ? e.message : "Try again." });
    } finally {
      setFunding(false);
    }
  };

  const copyEscrow = () => {
    if (!agent.escrow_address) return;
    navigator.clipboard?.writeText(agent.escrow_address);
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
  };

  const realMode = paymentMode === "real";
  const canFund = !(realMode && isDemoWallet);

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Panel
          title={`Fund ${agent.name}`}
          description="Move USDC from your wallet into the agent's escrow. This is the hard ceiling on its spending."
          action={
            <span
              className={cn(
                "rounded px-2 py-0.5 text-[10px] font-bold tracking-wide",
                realMode ? "bg-success/15 text-success" : "bg-warning/15 text-warning"
              )}
            >
              {realMode ? "REAL MODE" : "MOCK MODE"}
            </span>
          }
        >
          <div className="flex flex-col gap-4">
            <Input
              id="fund-amount"
              label="Amount"
              type="number"
              min="0"
              prefix="$"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
            <div className="rounded-lg border border-border bg-background/40 p-3.5">
              <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                Review
              </div>
              <div className="mt-2 flex items-center justify-between">
                <span className="text-sm text-muted-foreground">
                  Fund <span className="font-medium text-foreground">{agent.name}</span>
                </span>
                <span className="text-sm font-semibold tabular-nums text-foreground">
                  {formatUsdc(parseFloat(amount) || 0)}
                </span>
              </div>
              <div className="mt-1 flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Asset</span>
                <span className="font-medium text-foreground">USDC SPL</span>
              </div>
              <div className="mt-1 flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Network</span>
                <span className="font-medium text-foreground">
                  {realMode ? `Solana ${network === "mainnet-beta" ? "Mainnet" : "Devnet"}` : `Solana ${network === "mainnet-beta" ? "Mainnet" : "Devnet"} (simulated)`}
                </span>
              </div>
              {realMode && isDemoWallet && (
                <div className="mt-3 flex items-center gap-1.5 rounded-md border border-warning/30 bg-warning/10 px-2.5 py-2 text-xs text-warning animate-fade-in">
                  <ShieldCheck className="h-3.5 w-3.5 shrink-0" />
                  REAL MODE is active — connect a Phantom wallet to sign the transfer.
                </div>
              )}
              {confirmed && lastTx && (
                <div className="mt-3 flex flex-col gap-1 rounded-md border border-success/30 bg-success/10 px-2.5 py-2 text-xs font-medium text-success animate-fade-in">
                  {lastTx.kind === "mock" ? (
                    <div className="flex items-center gap-1.5">
                      <Check className="h-3.5 w-3.5" />
                      Escrow funded (SIMULATED) · {shortAddress(lastTx.signature, 8)}
                    </div>
                  ) : (
                    <div className="flex items-center justify-between gap-2">
                      <span className="flex items-center gap-1.5">
                        <Check className="h-3.5 w-3.5" /> Escrow funded on-chain
                      </span>
                      <a
                        href={explorerUrlForSignature(lastTx.signature)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 font-medium text-info hover:text-foreground"
                      >
                        View on Solana Explorer <ExternalLink className="h-3 w-3" />
                      </a>
                    </div>
                  )}
                </div>
              )}
            </div>
            <Button onClick={fund} disabled={funding || !(parseFloat(amount) > 0) || !canFund}>
              {funding ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowDownToLine className="h-4 w-4" />}
              {funding
                ? realMode
                  ? "Confirm in wallet…"
                  : "Funding (simulated)…"
                : realMode
                  ? `Fund ${agent.name}`
                  : `Fund ${agent.name} (simulated)`}
            </Button>
            {agent.status !== "active" && (
              <p className="text-xs text-warning">
                Agent is {agent.status} — it can hold funds but cannot spend until active.
              </p>
            )}
          </div>
        </Panel>

        <Panel title="Escrow" description="Where the agent's USDC lives on Solana">
          {loading && !agent.escrow_address ? (
            <div className="space-y-3">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              <div className="rounded-lg border border-border bg-background/40 p-3">
                <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                  Escrow address
                </div>
                <div className="mt-1 flex items-center gap-2">
                  <button
                    onClick={copyEscrow}
                    className="truncate font-mono text-xs text-foreground transition-colors hover:text-primary"
                    title={agent.escrow_address ?? undefined}
                  >
                    {agent.escrow_address ? shortAddress(agent.escrow_address, 12) : "Derived at first funding"}
                  </button>
                  {copied ? <Check className="h-3.5 w-3.5 shrink-0 text-success" /> : <Copy className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />}
                </div>
              </div>
              <div className="rounded-lg border border-border bg-background/40 p-3">
                <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                  Funding source wallet
                </div>
                <div className="mt-1 font-mono text-xs text-foreground">{shortAddress(address, 10)}</div>
              </div>
              <div className="rounded-lg border border-border bg-background/40 p-3">
                <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                  Available balance
                </div>
                <div className="mt-1 text-xl font-bold tabular-nums text-success">
                  {formatUsdc(agent.balance)} <span className="text-xs font-medium text-muted-foreground">USDC</span>
                </div>
              </div>
              {!realMode && (
                <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                  <span className="rounded bg-warning/15 px-1.5 py-0.5 text-[10px] font-bold text-warning">MOCK</span>
                  Simulated escrow — no on-chain account or explorer link in MOCK MODE.
                </div>
              )}
              {realMode && agent.escrow_address && (
                <a
                  href={explorerAddressUrl(agent.escrow_address, network === "mainnet-beta" ? "mainnet-beta" : "devnet")}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs font-medium text-info hover:text-foreground"
                >
                  View escrow on Solana Explorer <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </div>
          )}
        </Panel>
      </div>

      <Panel title="Agent transactions" description="Every payment signed by this escrow" bodyClassName="p-3 sm:p-4">
        {transactions.length ? (
          <TransactionTable transactions={transactions} hideAgent />
        ) : (
          <EmptyState
            icon={Wallet}
            title="No transactions yet"
            description="Fund the agent and run a task to populate its ledger."
          />
        )}
      </Panel>
    </div>
  );
}

// ---------------------------------------------------------------- tasks

function TasksTab({
  agent,
  address,
  runs,
  onTransaction,
}: {
  agent: Agent;
  address: string;
  runs: TaskRunResult[];
  onTransaction: () => void;
}) {
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <Panel
        title="Give the agent a task"
        description="The AI proposes an action. The policy engine decides. The chain executes — never the LLM directly."
      >
        <TaskRunner agent={agent} address={address} onTransaction={onTransaction} />
      </Panel>

      <Panel
        title="Run history"
        description="Recent task executions"
        bodyClassName={runs.length ? "p-0" : undefined}
      >
        {runs.length === 0 ? (
          <EmptyState
            icon={ShieldCheck}
            title="No runs yet"
            description="Run a task and its execution log will appear here."
          />
        ) : (
          <div className="flex flex-col divide-y divide-border/60">
            {runs.map((r) => (
              <div key={r.run_id} className="flex items-center justify-between gap-3 px-4 py-3 sm:px-5">
                <div className="min-w-0">
                  <div className="text-sm font-medium text-foreground">Run #{r.run_id}</div>
                  <div className="truncate text-xs text-muted-foreground">
                    {r.error ?? (r.blocked ? "Policy engine blocked a payment" : r.result ? "Completed a payment flow" : "Running")}
                  </div>
                </div>
                <TransactionStatusBadge
                  status={
                    r.blocked ? "rejected" : r.error ? "failed" : r.status === "completed" ? "executed" : "pending"
                  }
                />
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}

// ---------------------------------------------------------------- activity

function AgentActivity({
  transactions,
  agentName,
}: {
  transactions: Transaction[];
  agentName: string;
}) {
  const events = useMemo(
    () =>
      transactions
        .map((t) => transactionToActivity(t, agentName))
        .filter((e): e is NonNullable<typeof e> => e !== null),
    [transactions, agentName]
  );
  return (
    <ActivityFeed
      events={events}
      emptyTitle="No activity yet"
      emptyDescription="Payments and policy decisions for this agent will stream in here."
    />
  );
}

// ---------------------------------------------------------------- skeleton

function AgentDetailSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      <div className="h-8 w-24 animate-pulse rounded bg-muted" />
      <div className="flex items-center gap-4">
        <div className="h-14 w-14 animate-pulse rounded-xl bg-muted" />
        <div className="flex-1 space-y-2">
          <div className="h-6 w-48 animate-pulse rounded bg-muted" />
          <div className="h-4 w-72 animate-pulse rounded bg-muted/60" />
        </div>
        <div className="animate-pulse">
          <Skeleton className="h-9 w-28" />
        </div>
      </div>
      <div className="h-14 animate-pulse rounded-xl border border-border bg-card" />
      <div className="h-10 animate-pulse rounded bg-secondary/60" />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="h-24 animate-pulse rounded-xl border border-border bg-card" />
        ))}
      </div>
    </div>
  );
}