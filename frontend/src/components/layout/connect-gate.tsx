"use client";

import { Wallet, Loader2, Sparkles } from "lucide-react";
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
          Connect a wallet to continue
        </h3>
        <p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">
          Connect a Solana wallet, or use the simulated wallet to explore the full
          demo without one.
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
          <>
            <Sparkles className="h-4 w-4" />
            Connect demo wallet
          </>
        )}
      </button>
    </div>
  );
}