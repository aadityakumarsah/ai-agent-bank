"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { ApprovalRequest } from "@/lib/types";
import { seedApprovals } from "@/lib/demo";
import { api } from "@/lib/api";
import { useToast } from "@/components/ui/toast";
import { formatUsdc } from "@/lib/utils";

interface ApprovalSyncTx {
  id: number;
  agentId?: number;
  agentName?: string;
  amount: number;
  currency?: string;
  recipientName?: string | null;
  recipientAddress?: string;
  category?: string | null;
  status: string;
}

interface ApprovalsContextValue {
  requests: ApprovalRequest[];
  pendingCount: number;
  approveRequest: (id: string) => void;
  rejectRequest: (id: string) => void;
  syncFromTransactions: (txs: ApprovalSyncTx[], agentIdToName?: Map<number, string>) => void;
  loadBackendApprovals: (wallet: string) => void;
}

const ApprovalsContext = createContext<ApprovalsContextValue>({
  requests: [],
  pendingCount: 0,
  approveRequest: () => {},
  rejectRequest: () => {},
  syncFromTransactions: () => {},
  loadBackendApprovals: () => {},
});

export function useApprovals() {
  return useContext(ApprovalsContext);
}

export function ApprovalsProvider({ children }: { children: React.ReactNode }) {
  const { toast } = useToast();
  const [requests, setRequests] = useState<ApprovalRequest[]>([]);
  const seeded = useRef<Set<number>>(new Set());

  // Only seed simulated demo approvals when the backend is in DEMO_MODE. In
  // real mode the approvals list is 100% real pending transactions
  // (syncFromTransactions) — no fabricated requests.
  useEffect(() => {
    let cancelled = false;
    api
      .getStatus()
      .then((s) => {
        if (!cancelled && s.demo_mode) {
          setRequests(seedApprovals());
        }
      })
      .catch(() => {
        /* offline — leave empty */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const loadBackendApprovals = useCallback(
    (wallet: string) => {
      if (!wallet) return;
      let cancelled = false;
      api
        .listTransactions(wallet)
        .then((txs) => {
          if (cancelled) return;
          const now = Date.now();
          const fresh: ApprovalRequest[] = txs
            .filter(
              (t) =>
                (t.status === "pending" || t.status === "approved") &&
                !seeded.current.has(t.id)
            )
            .map((t): ApprovalRequest => {
              seeded.current.add(t.id);
              return {
                id: `tx-${t.id}`,
                agentName: t.recipient_name ?? `Agent #${t.agent_id}`,
                agentId: t.agent_id,
                amount: t.amount,
                currency: t.currency ?? "USDC",
                reason: "Policy check — amount above approval threshold.",
                policyNote:
                  "Transactions above the approval threshold require human approval.",
                recipientName: t.recipient_name ?? undefined,
                recipient: t.recipient_address,
                category: t.category ?? undefined,
                transactionId: t.id,
                expiresAt: now + 15 * 60 * 1000,
                status: "pending",
              };
            });
          if (fresh.length) {
            setRequests((prev) => [...prev, ...fresh]);
          }
        })
        .catch(() => {
          /* offline */
        });
      return () => {
        cancelled = true;
      };
    },
    []
  );

  const syncFromTransactions = useCallback(
    (txs: ApprovalSyncTx[], agentIdToName?: Map<number, string>) => {
      const now = Date.now();
      const fresh: ApprovalRequest[] = txs
        .filter(
          (t) =>
            (t.status === "pending" || t.status === "approved") && !seeded.current.has(t.id)
        )
        .map((t): ApprovalRequest => {
          seeded.current.add(t.id);
          return {
            id: `tx-${t.id}`,
            agentName:
              t.agentName ??
              agentIdToName?.get(t.agentId ?? -1) ??
              `Agent #${t.agentId ?? ""}`,
            agentId: t.agentId,
            amount: t.amount,
            currency: t.currency ?? "USDC",
            reason: "Policy check — amount above approval threshold.",
            policyNote: "Transactions above the approval threshold require human approval.",
            recipientName: t.recipientName ?? undefined,
            recipient: t.recipientAddress,
            category: t.category ?? undefined,
            transactionId: t.id,
            expiresAt: now + 15 * 60 * 1000,
            status: "pending",
          };
        });
      if (fresh.length) {
        setRequests((prev) => [...prev, ...fresh]);
      }
    },
    []
  );

  const approveRequest = useCallback(
    async (id: string) => {
      const target = requests.find((r) => r.id === id);
      setRequests((prev) => prev.map((r) => (r.id === id ? { ...r, status: "approved" } : r)));
      if (target) {
        toast({
          type: "success",
          title: "Approval granted",
          description: `${target.agentName} can now spend ${formatUsdc(target.amount)} ${target.currency}.`,
        });
      }
    },
    [requests, toast]
  );

  const rejectRequest = useCallback(
    async (id: string) => {
      const target = requests.find((r) => r.id === id);
      setRequests((prev) => prev.map((r) => (r.id === id ? { ...r, status: "rejected" } : r)));
      if (target) {
        toast({
          type: "warning",
          title: "Approval rejected",
          description: `${target.agentName}'s request for ${formatUsdc(target.amount)} ${target.currency} was denied.`,
        });
      }
    },
    [requests, toast]
  );

  const pendingCount = useMemo(
    () =>
      requests.filter(
        (r) => r.status === "pending" && (!r.expiresAt || r.expiresAt > Date.now())
      ).length,
    [requests]
  );

  const value = useMemo(
    () => ({
      requests,
      pendingCount,
      approveRequest,
      rejectRequest,
      syncFromTransactions,
      loadBackendApprovals,
    }),
    [requests, pendingCount, approveRequest, rejectRequest, syncFromTransactions, loadBackendApprovals]
  );

  return <ApprovalsContext.Provider value={value}>{children}</ApprovalsContext.Provider>;
}