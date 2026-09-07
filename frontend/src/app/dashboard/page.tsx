"use client";

import { AppShell } from "@/components/layout/app-shell";
import { Overview } from "@/components/dashboard/overview";
import { ConnectGate } from "@/components/layout/connect-gate";

export default function DashboardPage() {
  return (
    <AppShell>
      <ConnectGate>
        <Overview />
      </ConnectGate>
    </AppShell>
  );
}