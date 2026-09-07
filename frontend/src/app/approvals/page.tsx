"use client";

import { AppShell } from "@/components/layout/app-shell";
import { ConnectGate } from "@/components/layout/connect-gate";
import { ApprovalsPage } from "@/components/approvals/approvals-page";

export default function ApprovalsPageRoute() {
  return (
    <AppShell>
      <ConnectGate>
        <ApprovalsPage />
      </ConnectGate>
    </AppShell>
  );
}