"use client";

import { useCallback, useEffect, useState } from "react";
import { Store, Zap, ShieldOff, Sparkles, Package } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Tabs } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { DirectorySection } from "@/components/marketplace/directory-section";
import { DemoSection } from "@/components/marketplace/demo-section";
import { ScenarioSection } from "@/components/marketplace/scenario-section";
import { RealMarketplaceSection } from "@/components/marketplace/real-marketplace-section";
import { useConfigStatus } from "@/hooks/use-config-status";
import { useWalletConnection } from "@/components/wallet/wallet-context";
import { api } from "@/lib/api";
import type { MarketService } from "@/lib/types";

type Tab = "directory" | "providers" | "killer" | "failed" | "scenarios";

export function MarketplacePage() {
  const [tab, setTab] = useState<Tab>("directory");
  const [services, setServices] = useState<MarketService[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const { status } = useConfigStatus();
  const { address } = useWalletConnection();
  const demoMode = status?.demo_mode === true;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listServices();
      setServices(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load the service directory");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const paidCount = services.filter((s) => s.requires_payment).length;

  return (
    <div className="flex flex-col">
      <PageHeader
        eyebrow={
          <span className="inline-flex items-center gap-1.5">
            <Store className="h-3 w-3" /> Autonomium
          </span>
        }
        title="Marketplace"
        description="A service directory the agents can pay to use. Request an API, the bank validates policy, USDC moves, and the agent gets its result — no human in the loop, no uncontrolled spending."
        actions={
          <>
            <Badge variant="outline" className="gap-1">
              {services.length} services
            </Badge>
            <Badge variant="warning" className="gap-1">
              {paidCount} payable
            </Badge>
            {demoMode && (
              <Badge variant="warning" className="gap-1">
                <Sparkles className="h-3 w-3" /> DEMO MODE
              </Badge>
            )}
          </>
        }
      />

      <Tabs<Tab>
        tabs={[
          { value: "directory", label: "Service Directory", icon: <Store className="h-4 w-4" /> },
          { value: "providers", label: "Providers", icon: <Package className="h-4 w-4" /> },
          { value: "killer", label: "Autonomous Purchase", icon: <Zap className="h-4 w-4" /> },
          { value: "failed", label: "Blocked Payment", icon: <ShieldOff className="h-4 w-4" /> },
          ...(demoMode
            ? [{ value: "scenarios" as Tab, label: "One-click Demos", icon: <Sparkles className="h-4 w-4" /> }]
            : []),
        ]}
        value={tab}
        onChange={setTab}
      />

      <div className="mt-6">
        {tab === "directory" && (
          <DirectorySection
            services={services}
            loading={loading}
            error={error}
            onRetry={() => void load()}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        )}
        {tab === "providers" && <RealMarketplaceSection address={address} />}
        {tab === "killer" && <DemoSection kind="killer" />}
        {tab === "failed" && <DemoSection kind="failed" />}
        {tab === "scenarios" && demoMode && <ScenarioSection />}
      </div>
    </div>
  );
}