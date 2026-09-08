"use client";

import { Wallet, Loader2 } from "lucide-react";
import { useWalletConnection } from "@/components/wallet/wallet-context";

export function ConnectGate({ children }: { children: React.ReactNode }) {
  const { connected, connect, connecting } = useWalletConnection();

  if (connected) return <>{children}</>;

  return (
    <div className="flex flex-col items-center gap-4 rounded-xl border border-dashed border-border bg-card/40 px-6 py-20 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full border border-border bg-secondary text-muted-foreground">
        <Wallet className="h-5 w-5" />
      </div>
      <div>
        <h3 className="text-sm font-semibold text-foreground">
          Connect your Solana wallet
        </h3>
        <p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">
          Your wallet signs every funding transfer and approval. It keeps
          full control — the agent can never spend beyond the limits you set.
        </p>
      </div>
      <button
        onClick={connect}
        disabled={connecting}
        className="inline-flex h-9 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-50"
      >
        {connecting ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Wallet className="h-4 w-4" />
        )}
        {connecting ? "Connecting…" : "Connect wallet"}
      </button>
      <p className="text-xs text-muted-foreground">
        Solflare or Phantom browser extension required to sign real USDC transfers.
      </p>
    </div>
  );
}