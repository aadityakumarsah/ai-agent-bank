"use client";

import { AppShell } from "@/components/layout/app-shell";
import { useWalletConnection } from "@/components/wallet/wallet-context";
import { CreateAgentWizard } from "@/components/agent/create-agent-wizard";
import { PageHeader } from "@/components/layout/page-header";

export default function NewAgentPage() {
  const { connected } = useWalletConnection();

  return (
    <AppShell>
      {connected ? (
        <div className="flex flex-col gap-6">
          <PageHeader
            title="Create a new agent"
            description="Fund it, set its policy, and protect its spending before it ever transacts."
          />
          <CreateAgentWizard />
        </div>
      ) : (
        <div className="py-24 text-center text-muted-foreground">
          Connect a wallet to create an agent.
        </div>
      )}
    </AppShell>
  );
}