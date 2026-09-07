"use client";

import { AppShell } from "@/components/layout/app-shell";
import { ConnectGate } from "@/components/layout/connect-gate";
import { SettingsPage } from "@/components/settings/settings-page";

export default function SettingsPageRoute() {
  return (
    <AppShell>
      <ConnectGate>
        <SettingsPage />
      </ConnectGate>
    </AppShell>
  );
}