"use client";

import { AppShell } from "@/components/layout/app-shell";
import { ConnectGate } from "@/components/layout/connect-gate";
import { AgentsPage } from "@/components/agents/agents-page";

export default function AgentsPageRoute() {
  return (
    <AppShell>
      <ConnectGate>
        <AgentsPage />
      </ConnectGate>
    </AppShell>
  );
}