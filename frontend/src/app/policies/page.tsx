"use client";

import { AppShell } from "@/components/layout/app-shell";
import { ConnectGate } from "@/components/layout/connect-gate";
import { PoliciesPage } from "@/components/policies/policies-page";

export default function PoliciesPageRoute() {
  return (
    <AppShell>
      <ConnectGate>
        <PoliciesPage />
      </ConnectGate>
    </AppShell>
  );
}