"use client";

import React, { createContext, useCallback, useContext, useMemo, useState } from "react";

import { DEMO_ADDRESS } from "./demo-address";

interface WalletContextValue {
  connected: boolean;
  connecting: boolean;
  address: string | null;
  isDemo: boolean;
  connect: () => Promise<void>;
  disconnect: () => void;
  error: string | null;
}

const WalletContext = createContext<WalletContextValue>({
  connected: false,
  connecting: false,
  address: null,
  isDemo: false,
  connect: async () => {},
  disconnect: () => {},
  error: null,
});

export function useWalletConnection() {
  return useContext(WalletContext);
}

export function WalletProvider({ children }: { children: React.ReactNode }) {
  const [address, setAddress] = useState<string | null>(null);
  const [isDemo, setIsDemo] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const connect = useCallback(async () => {
    setError(null);
    setConnecting(true);
    try {
      // Try real Solana wallet adapter first (Phantom etc.)
      const { tryConnect } = await import("@/components/wallet/adapters");
      const adapter = await tryConnect();
      if (adapter) {
        setAddress(adapter.publicKey.toBase58());
        setIsDemo(false);
        return;
      }
      // Fallback to demo wallet so the full UX is demoable without a wallet.
      const { default: connectDemo } = await import("@/components/wallet/demo-connect");
      const demoAddr = connectDemo();
      setAddress(demoAddr);
      setIsDemo(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to connect wallet");
    } finally {
      setConnecting(false);
    }
  }, []);

  const disconnect = useCallback(async () => {
    try {
      const { tryDisconnect } = await import("@/components/wallet/adapters");
      await tryDisconnect();
    } catch {
      /* ignore */
    }
    setAddress(null);
    setIsDemo(false);
    setError(null);
  }, []);

  const value = useMemo(
    () => ({
      connected: !!address,
      connecting,
      address,
      isDemo,
      connect,
      disconnect,
      error,
    }),
    [address, isDemo, connecting, connect, disconnect, error]
  );

  return <WalletContext.Provider value={value}>{children}</WalletContext.Provider>;
}