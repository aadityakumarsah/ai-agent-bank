"use client";

import { useEffect, useMemo } from "react";
import { Info, Inbox, CheckCircle2, XCircle, ShieldCheck } from "lucide-react";
import { useApprovals } from "@/components/approvals/approvals-context";
import { ApprovalCard } from "@/components/approvals/approval-card";
import { useBankData } from "@/hooks/use-bank-data";
import { useWalletConnection } from "@/components/wallet/wallet-context";
import { api } from "@/lib/api";
import { useToast } from "@/components/ui/toast";
import { PageHeader } from "@/components/layout/page-header";
import { Panel } from "@/components/ui/panel";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { summarizeAgents } from "@/lib/activity";
import { formatUsdc, shortAddress } from "@/lib/utils";

export function ApprovalsPage() {
  const {
    requests,
    pendingCount,
    approveRequest,
    rejectRequest,
    syncFromTransactions,
    loadBackendApprovals,
  } = useApprovals();
  const { agents, transactions, error, load } = useBankData();
  const { address, connected } = useWalletConnection();
  const { toast } = useToast();

  // In real mode (non-demo), fetch pending transactions from the backend
  // whenever the wallet address changes.
  useEffect(() => {
    if (connected && address) {
      loadBackendApprovals(address);
    }
  }, [connected, address, loadBackendApprovals]);

  useEffect(() => {
    if (transactions.length) {
      const idToName = summarizeAgents(agents);
      syncFromTransactions(transactions, idToName);
    }
  }, [transactions, agents, syncFromTransactions]);

  const handleApprove = async (id: string) => {
    const req = requests.find((r) => r.id === id);
    if (req?.transactionId && address) {
      try {
        await api.approveTransaction(address, req.transactionId);
      } catch (e) {
        toast({
          type: "error",
          title: "Could not approve",
          description: e instanceof Error ? e.message : "Approval failed",
        });
        return;
      }
    }
    approveRequest(id);
    load();
  };

  const handleReject = async (id: string) => {
    const req = requests.find((r) => r.id === id);
    if (req?.transactionId && address) {
      try {
        await api.rejectTransaction(address, req.transactionId);
      } catch (e) {
        toast({
          type: "error",
          title: "Could not reject",
          description: e instanceof Error ? e.message : "Rejection failed",
        });
        return;
      }
    }
    rejectRequest(id);
    load();
  };

  const pending = useMemo(
    () => requests.filter((r) => r.status === "pending" && r.expiresAt > Date.now()),
    [requests]
  );
  const decided = useMemo(
    () =>
      requests
        .filter((r) => r.status !== "pending" || r.expiresAt <= Date.now())
        .sort((a, b) => b.expiresAt - a.expiresAt),
    [requests]
  );

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Approvals"
        description="Requests that breached the approval threshold and need a human's final word. Approvals expire if you don't act in time."
      />

      {error && <ErrorState description={error} onRetry={() => void load()} />}

      <div className="flex items-start gap-2.5 rounded-lg border border-info/25 bg-info/5 px-4 py-3">
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-info" />
        <p className="text-xs leading-relaxed text-muted-foreground">
          When the policy engine marks a request <span className="font-medium text-foreground">Approval Required</span>,
          it pauses the agent task and queues the decision here. Approve to release the
          payment, reject to block it and return control to the agent. Requests that pass
          the threshold in <span className="font-medium text-foreground">REAL MODE</span> are stored on the backend —{" "}
          <span className="font-medium text-foreground">MOCK MODE</span> requests are simulated locally for the demo.
        </p>
      </div>

      <div>
        <div className="mb-3 flex items-center gap-2">
          <h2 className="text-sm font-semibold text-foreground">Pending decisions</h2>
          <span className="rounded-full bg-primary/15 px-2 py-0.5 text-xs font-bold text-primary tabular-nums">
            {pendingCount}
          </span>
        </div>
        {pending.length === 0 ? (
          <EmptyState
            icon={Inbox}
            title="Queue is clear"
            description="No requests awaiting approval. Give an agent a task that crosses the approval threshold to see one here."
          />
        ) : (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-3">
            {pending.map((r) => (
              <ApprovalCard
                key={r.id}
                request={r}
                onApprove={handleApprove}
                onReject={handleReject}
              />
            ))}
          </div>
        )}
      </div>

      {decided.length > 0 && (
        <Panel
          title="Decision history"
          description="Recent approvals and rejections from this session"
          bodyClassName="p-0"
        >
          <div className="flex flex-col divide-y divide-border/60">
            {decided.map((r) => (
              <div key={r.id} className="flex items-center justify-between gap-3 px-4 py-3 sm:px-5">
                <div className="flex items-center gap-3">
                  {r.status === "approved" ? (
                    <CheckCircle2 className="h-4 w-4 text-success" />
                  ) : (
                    <XCircle className="h-4 w-4 text-destructive" />
                  )}
                  <div className="min-w-0">
                    <div className="truncate text-sm text-foreground">
                      {r.agentName}
                      <span className="mx-1.5 text-muted-foreground">&middot;</span>
                      <span className="font-semibold tabular-nums">
                        {formatUsdc(r.amount)} {r.currency}
                      </span>
                    </div>
                    <div className="truncate text-xs text-muted-foreground">
                      {r.status === "expired" ? "Expired before decision" : r.status === "approved" ? "Approved" : "Rejected"}
                      {r.recipient ? ` · ${shortAddress(r.recipient, 5)}` : ""}
                    </div>
                  </div>
                </div>
                <span
                  className={`shrink-0 rounded px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${
                    r.status === "approved"
                      ? "bg-success/15 text-success"
                      : "bg-destructive/10 text-destructive"
                  }`}
                >
                  {r.status === "expired" ? "Expired" : r.status}
                </span>
              </div>
            ))}
          </div>
        </Panel>
      )}

      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <ShieldCheck className="h-4 w-4 text-primary" />
        The policy engine never auto-approves above the threshold — the human is always the
        final authority.
      </div>
    </div>
  );
}