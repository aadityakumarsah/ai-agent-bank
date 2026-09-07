"use client";

import { ArrowDownRight, Check, ExternalLink, ShieldAlert, X } from "lucide-react";
import type { Transaction } from "@/lib/types";
import { CATEGORY_LABELS } from "@/lib/types";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { TransactionStatusBadge } from "@/components/ui/status-badge";
import { formatUsdc, formatTime, shortAddress, explorerTxUrl } from "@/lib/utils";
import { ArrowLeftRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { isSimulatedSignature } from "@/lib/solana";

function policySummary(tx: Transaction): { label: string; tone: "success" | "destructive" | "neutral" } {
  if (tx.status === "executed") return { label: "Allowed", tone: "success" };
  if (tx.status === "rejected")
    return {
      label: tx.rejection_reason
        ? tx.rejection_reason.split(":")[0].split(" (")[0]
        : "Policy denied",
      tone: "destructive",
    };
  if (tx.status === "pending") return { label: "Awaiting approval", tone: "neutral" };
  if (tx.status === "failed") return { label: "Execution failed", tone: "destructive" };
  return { label: "Approved", tone: "neutral" };
}

function PolicyCell({ tx }: { tx: Transaction }) {
  const p = policySummary(tx);
  if (p.tone === "success") {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs font-medium text-success">
        <span className="flex h-4 w-4 items-center justify-center rounded-full bg-success/15">
          <Check className="h-2.5 w-2.5" />
        </span>
        {p.label}
      </span>
    );
  }
  if (p.tone === "destructive") {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs font-medium text-destructive" title={tx.rejection_reason ?? undefined}>
        <span className="flex h-4 w-4 items-center justify-center rounded-full bg-destructive/15">
          <X className="h-2.5 w-2.5" />
        </span>
        {p.label}
      </span>
    );
  }
  return <span className="text-xs text-muted-foreground">{p.label}</span>;
}

export function TransactionTable({
  transactions,
  hideAgent,
  emptyTitle = "No transactions yet",
  emptyDescription = "Transactions will appear here when agents run tasks.",
  network = "devnet",
}: {
  transactions: Transaction[];
  hideAgent?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  network?: "devnet" | "mainnet-beta";
}) {
  if (transactions.length === 0) {
    return (
      <EmptyState
        icon={ArrowLeftRight}
        title={emptyTitle}
        description={emptyDescription}
      />
    );
  }

  return (
    <Table>
      <THead>
        <tr>
          <TH className="pl-0">Time</TH>
          {!hideAgent && <TH>Agent</TH>}
          <TH className="text-right">Amount</TH>
          <TH>Recipient</TH>
          <TH className="hidden md:table-cell">Category</TH>
          <TH>Status</TH>
          <TH className="hidden md:table-cell">Policy</TH>
          <TH className="pr-0 text-right">Transaction</TH>
        </tr>
      </THead>
      <TBody>
        {transactions.map((tx) => {
          const isOut = tx.status === "executed" || tx.status === "pending" || tx.status === "approved";
          return (
            <TR key={tx.id}>
              <TD className="whitespace-nowrap pl-0 font-mono text-xs text-muted-foreground">
                {formatTime(tx.created_at)}
              </TD>
              {!hideAgent && (
                <TD className="whitespace-nowrap text-xs font-medium text-foreground">
                  Agent #{tx.agent_id}
                </TD>
              )}
              <TD className="whitespace-nowrap text-right">
                <span
                  className={cn(
                    "inline-flex items-center gap-1 font-semibold tabular-nums",
                    tx.status === "rejected"
                      ? "text-destructive"
                      : tx.status === "executed"
                        ? "text-foreground"
                        : "text-muted-foreground"
                  )}
                >
                  <ArrowDownRight
                    className={cn("h-3.5 w-3.5", tx.status === "rejected" && "text-destructive")}
                  />
                  {formatUsdc(tx.amount)}
                  <span className="text-[10px] font-normal text-muted-foreground">
                    {tx.currency}
                  </span>
                </span>
              </TD>
              <TD className="max-w-[10rem]">
                <div className="truncate text-xs" title={tx.recipient_address}>
                  {tx.recipient_name ?? shortAddress(tx.recipient_address, 6)}
                </div>
                {tx.recipient_name && (
                  <div className="truncate font-mono text-[10px] text-muted-foreground">
                    {shortAddress(tx.recipient_address, 5)}
                  </div>
                )}
              </TD>
              <TD className="hidden md:table-cell">
                {tx.category ? (
                  <span className="rounded border border-border bg-card px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                    {CATEGORY_LABELS[tx.category] ?? tx.category}
                  </span>
                ) : (
                  <span className="text-xs text-muted-foreground">—</span>
                )}
              </TD>
              <TD>
                <TransactionStatusBadge status={tx.status} />
              </TD>
              <TD className="hidden md:table-cell">
                <PolicyCell tx={tx} />
              </TD>
              <TD className="whitespace-nowrap pr-0 text-right">
                {tx.tx_hash ? (
                  isSimulatedSignature(tx.tx_hash) ? (
                    <span
                      className="inline-flex items-center gap-1 font-mono text-xs text-muted-foreground"
                      title="MOCK MODE — simulated transaction, nothing on-chain"
                    >
                      <ShieldAlert className="h-3 w-3 text-warning" />
                      {shortAddress(tx.tx_hash, 6)}
                    </span>
                  ) : (
                    <a
                      href={explorerTxUrl(tx.tx_hash, network)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 font-mono text-xs text-info transition-colors hover:text-foreground"
                    >
                      {shortAddress(tx.tx_hash, 6)}
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  )
                ) : (
                  <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                    <ShieldAlert className="h-3 w-3" />
                    {tx.status === "rejected" ? "No tx" : "—"}
                  </span>
                )}
              </TD>
            </TR>
          );
        })}
      </TBody>
    </Table>
  );
}

export function TransactionTableSkeleton({ rows = 6, hideAgent }: { rows?: number; hideAgent?: boolean }) {
  return (
    <div className="flex flex-col gap-2.5">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 border-b border-border/60 pb-2.5">
          <Skeleton className="h-3 w-16" />
          {!hideAgent && <Skeleton className="h-3 w-14" />}
          <Skeleton className="ml-auto h-3 w-20" />
          <Skeleton className="h-5 w-24" />
          <div className="hidden md:block">
            <Skeleton className="h-3 w-16" />
          </div>
          <Skeleton className="h-5 w-20" />
        </div>
      ))}
    </div>
  );
}