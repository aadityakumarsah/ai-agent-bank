"use client";

import { AppShell } from "@/components/layout/app-shell";
import { useWalletConnection } from "@/components/wallet/wallet-context";
import { AgentDetail } from "@/components/agent/agent-detail";

export default function AgentPage({ params }: { params: { id: string } }) {
  const { connected } = useWalletConnection();

  return (
    <AppShell>
      {connected ? (
        <AgentDetail agentId={Number(params.id)} />
      ) : (
        <div className="py-24 text-center text-muted-foreground">
          Connect a wallet to view this agent.
        </div>
      )}
    </AppShell>
  );
}