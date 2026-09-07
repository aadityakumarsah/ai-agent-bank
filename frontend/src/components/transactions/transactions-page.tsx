"use client";

import { useMemo, useState } from "react";
import { ArrowLeftRight, Search } from "lucide-react";
import { useBankData } from "@/hooks/use-bank-data";
import { PageHeader } from "@/components/layout/page-header";
import { Panel } from "@/components/ui/panel";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import {
  TransactionTable,
  TransactionTableSkeleton,
} from "@/components/transactions/transaction-table";
import { TX_STATUS_LABELS } from "@/lib/types";
import { cn } from "@/lib/utils";

const STATUS_FILTERS = ["all", "executed", "pending", "rejected", "approved", "failed"] as const;

export function TransactionsPage() {
  const { transactions, loading, error, load, status } = useBankData();
  const [filter, setFilter] = useState<(typeof STATUS_FILTERS)[number]>("all");
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    let list = transactions;
    if (filter !== "all") {
      list = list.filter((t) => t.status === filter);
    }
    const q = query.trim().toLowerCase();
    if (q) {
      list = list.filter(
        (t) =>
          t.recipient_name?.toLowerCase().includes(q) ||
          t.recipient_address.toLowerCase().includes(q) ||
          String(t.agent_id).includes(q) ||
          (t.category ?? "").toLowerCase().includes(q)
      );
    }
    return list;
  }, [transactions, filter, query]);

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: transactions.length };
    for (const s of STATUS_FILTERS) {
      if (s !== "all") c[s] = transactions.filter((t) => t.status === s).length;
    }
    return c;
  }, [transactions]);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Transactions"
        description="The complete audit trail — every attempt the policy engine allowed or blocked."
      />

      {error && <ErrorState description={error} onRetry={() => void load()} />}

      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-1.5">
            {STATUS_FILTERS.map((s) => (
              <button
                key={s}
                onClick={() => setFilter(s)}
                className={cn(
                  "rounded-full border px-3 py-1.5 text-xs font-medium transition-colors",
                  filter === s
                    ? "border-primary/40 bg-primary/10 text-primary"
                    : "border-border bg-card text-muted-foreground hover:text-foreground"
                )}
              >
                {s === "all" ? "All" : TX_STATUS_LABELS[s] ?? s}
                <span className="ml-1.5 tabular-nums text-muted-foreground">{counts[s] ?? 0}</span>
              </button>
            ))}
          </div>
          <div className="relative sm:w-64">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search recipient, agent…"
              className="h-9 w-full rounded-md border border-input bg-card pl-8 pr-3 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          </div>
        </div>

        <Panel bodyClassName="p-3 sm:p-4">
          {loading && transactions.length === 0 ? (
            <TransactionTableSkeleton rows={8} />
          ) : filtered.length === 0 ? (
            <EmptyState
              icon={ArrowLeftRight}
              title={query || filter !== "all" ? "No matching transactions" : "No transactions yet"}
              description={
                query || filter !== "all"
                  ? "Try adjusting the filter or search query."
                  : "Transactions appear here when agents run tasks."
              }
            />
          ) : (
            <TransactionTable transactions={filtered} network={status?.payment_mode === "real" ? "devnet" : "devnet"} />
          )}
        </Panel>
      </div>
    </div>
  );
}