"use client";

import { AppShell } from "@/components/layout/app-shell";
import { ConnectGate } from "@/components/layout/connect-gate";
import { ActivityPage } from "@/components/activity/activity-page";

export default function ActivityPageRoute() {
  return (
    <AppShell>
      <ConnectGate>
        <ActivityPage />
      </ConnectGate>
    </AppShell>
  );
}