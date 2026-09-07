"use client";

import { useCallback, useEffect, useState } from "react";
import { useWalletConnection } from "@/components/wallet/wallet-context";
import { api } from "@/lib/api";
import type { Agent, Transaction, ConfigStatus } from "@/lib/types";
import { useConfigStatus } from "@/hooks/use-config-status";

export function useBankData() {
  const { address, connected } = useWalletConnection();
  const { status } = useConfigStatus();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!address) return;
    setLoading(true);
    setError(null);
    try {
      await api.ensureUser(address);
      const [agentsData, txsData] = await Promise.all([
        api.listAgents(address),
        api.listTransactions(address),
      ]);
      setAgents(agentsData);
      setTransactions(txsData);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, [address]);

  useEffect(() => {
    if (connected && address) void load();
  }, [connected, address, load]);

  return {
    agents,
    transactions,
    status,
    loading,
    error,
    load,
    setAgents,
    setTransactions,
  };
}

export type BankData = ReturnType<typeof useBankData>;