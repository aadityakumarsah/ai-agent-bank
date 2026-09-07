"use client";

import { AppShell } from "@/components/layout/app-shell";
import { ConnectGate } from "@/components/layout/connect-gate";
import { TransactionsPage } from "@/components/transactions/transactions-page";

export default function TransactionsPageRoute() {
  return (
    <AppShell>
      <ConnectGate>
        <TransactionsPage />
      </ConnectGate>
    </AppShell>
  );
}