"use client";

import { useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Plus, Wallet, TrendingUp, ArrowLeftRight, Inbox, AlertTriangle } from "lucide-react";
import { useBankData } from "@/hooks/use-bank-data";
import { useApprovals } from "@/components/approvals/approvals-context";
import { useLiveActivity } from "@/hooks/use-live-activity";
import { StatCard } from "@/components/ui/stat-card";
import { Panel } from "@/components/ui/panel";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { PageHeader } from "@/components/layout/page-header";
import { SpendingPanel, SpendingPanelSkeleton } from "@/components/dashboard/spending-panel";
import { ActivityFeed, ActivityFeedSkeleton } from "@/components/activity/activity-feed";
import { TransactionTable, TransactionTableSkeleton } from "@/components/transactions/transaction-table";
import { formatUsdc } from "@/lib/utils";
import { isToday } from "@/lib/utils";

function StatSkeleton() {
  return (
    <div className="space-y-3 rounded-xl border border-border bg-card p-4">
      <div className="h-3 w-24 animate-pulse rounded bg-muted" />
      <div className="h-7 w-28 animate-pulse rounded bg-muted" />
    </div>
  );
}

export function Overview() {
  const router = useRouter();
  const { agents, transactions, loading, error, load, status } = useBankData();
  const { pendingCount } = useApprovals();
  const { events, playing, toggleLive, clearSimulated } = useLiveActivity({
    transactions,
    runs: [],
    agents,
    live: true,
  });

  const todaySpending = useMemo(
    () =>
      transactions
        .filter((t) => t.status === "executed" && isToday(t.created_at))
        .reduce((s, t) => s + t.amount, 0),
    [transactions]
  );

  const totalFunds = useMemo(
    () => agents.reduce((s, a) => s + a.balance, 0),
    [agents]
  );

  const stateLoading = loading && agents.length === 0;

  if (stateLoading) {
    return (
      <div className="flex flex-col gap-6">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <SkeletonTitle />
          </div>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <StatSkeleton key={i} />
          ))}
        </div>
        <SpendingPanelSkeleton />
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
          <div className="lg:col-span-2">
            <Panel title={<SkeletonLine w={32} />}>
              <ActivityFeedSkeleton rows={4} />
            </Panel>
          </div>
          <div className="lg:col-span-3">
            <Panel title={<SkeletonLine w={40} />}>
              <TransactionTableSkeleton rows={4} />
            </Panel>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        eyebrow={
          status ? (
            <span className="inline-flex items-center gap-1.5">
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  status.payment_mode === "mock" ? "bg-warning" : "bg-success"
                }`}
              />
              {status.payment_mode === "mock" ? "MOCK MODE · backend demo" : "SOLANA DEVNET · LIVE"}
            </span>
          ) : undefined
        }
        title="Overview"
        description="Programmable money for AI agents. Fund them, bound them with policies, and watch every decision the policy engine makes."
        actions={
          <Button onClick={() => router.push("/agents/new")}>
            <Plus className="h-4 w-4" />
            Create agent
          </Button>
        }
      />

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-warning/30 bg-warning/5 px-4 py-3 text-sm text-warning">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <div className="min-w-0 flex-1">
            Backend unreachable — showing the interface with cached/empty data. Start the API
            server to load live state.
          </div>
          <Button variant="outline" size="sm" onClick={() => void load()}>
            Retry
          </Button>
        </div>
      )}

      {/* Stat cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Total Agent Funds"
          value={formatUsdc(totalFunds)}
          icon={Wallet}
          tone="success"
          hint={`${agents.length} agent${agents.length === 1 ? "" : "s"} · USDC`}
        />
        <StatCard
          label="Today's Spending"
          value={formatUsdc(todaySpending)}
          icon={TrendingUp}
          tone="primary"
          hint="Executed today"
        />
        <StatCard
          label="Transactions"
          value={transactions.length}
          icon={ArrowLeftRight}
          hint={`${transactions.filter((t) => t.status === "rejected").length} blocked`}
        />
        <StatCard
          label="Pending Approvals"
          value={pendingCount}
          icon={Inbox}
          tone="warning"
          hint="Awaiting your decision"
          onClick={() => router.push("/approvals")}
        />
      </div>

      {/* Agent spending */}
      <SpendingPanel agents={agents} transactions={transactions} />

      {/* Recent activity + recent transactions */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        <div className="lg:col-span-2">
          <Panel
            title="Activity"
            description="Policy decisions and payments in real time"
            action={
              <Link href="/activity">
                <Button variant="ghost" size="sm" className="h-7 text-xs">
                  View all
                </Button>
              </Link>
            }
          >
            <ActivityFeed
              events={events}
              live={playing}
              toggleLive={toggleLive}
              onClearSimulated={clearSimulated}
              compact
            />
          </Panel>
        </div>
        <div className="lg:col-span-3">
          <Panel
            title="Recent transactions"
            description="Every financial action — executed or blocked"
            action={
              <Link href="/transactions">
                <Button variant="ghost" size="sm" className="h-7 text-xs">
                  View all
                </Button>
              </Link>
            }
          >
            <TransactionTable transactions={transactions.slice(0, 8)} />
          </Panel>
        </div>
      </div>
    </div>
  );
}

function SkeletonTitle() {
  return <div className="h-7 w-40 animate-pulse rounded bg-muted" />;
}

function SkeletonLine({ w }: { w: number }) {
  return (
    <div className="h-4 animate-pulse rounded bg-muted/60" style={{ width: `${w * 4}px` }} />
  );
}