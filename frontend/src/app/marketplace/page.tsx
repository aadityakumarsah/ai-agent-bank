"use client";

import { AppShell } from "@/components/layout/app-shell";
import { ConnectGate } from "@/components/layout/connect-gate";
import { MarketplacePage } from "@/components/marketplace/marketplace-page";

export default function MarketplaceRoute() {
  return (
    <AppShell>
      <ConnectGate>
        <MarketplacePage />
      </ConnectGate>
    </AppShell>
  );
}