"use client";

import { useRouter } from "next/navigation";
import { Plus, Bot } from "lucide-react";
import { useBankData } from "@/hooks/use-bank-data";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { AgentCard, AgentCardSkeleton } from "@/components/agents/agent-card";
import { Panel } from "@/components/ui/panel";

export function AgentsPage() {
  const router = useRouter();
  const { agents, transactions, loading, error, load } = useBankData();

  const active = agents.filter((a) => a.status === "active").length;
  const totalFunds = agents.reduce((s, a) => s + a.balance, 0);

  if (loading && agents.length === 0) {
    return (
      <div className="flex flex-col gap-6">
        <div>
          <div className="h-7 w-32 animate-pulse rounded bg-muted" />
          <div className="mt-2 h-4 w-64 animate-pulse rounded bg-muted/60" />
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <AgentCardSkeleton key={i} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Agents"
        description={
          <>
            <span className="font-medium text-foreground">{agents.length}</span> agent
            {agents.length === 1 ? "" : "s"} · {active} active ·{" "}
            <span className="tabular-nums">${totalFunds.toFixed(2)}</span> funded
          </>
        }
        actions={
          <Button onClick={() => router.push("/agents/new")}>
            <Plus className="h-4 w-4" />
            Create agent
          </Button>
        }
      />

      {error && <ErrorState description={error} onRetry={() => void load()} />}

      {agents.length === 0 ? (
        <Panel>
          <EmptyState
            icon={Bot}
            title="No agents yet"
            description="Create an agent, fund it with USDC, and define its spending permissions. It proposes — the policy engine decides."
            actionLabel="Create your first agent"
            onAction={() => router.push("/agents/new")}
          />
        </Panel>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {agents.map((agent) => (
            <AgentCard key={agent.id} agent={agent} transactions={transactions} />
          ))}
        </div>
      )}
    </div>
  );
}