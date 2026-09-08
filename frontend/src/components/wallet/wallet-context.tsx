"use client";

import React, { createContext, useCallback, useContext, useMemo, useState } from "react";
import { Keypair } from "@solana/web3.js";

import { DEMO_ADDRESS } from "./demo-address";

interface WalletContextValue {
  connected: boolean;
  connecting: boolean;
  address: string | null;
  isDemo: boolean;
  signingKey: Keypair | null;
  connect: () => Promise<void>;
  connectWithKey: (secretKey: string) => Promise<string | null>;
  disconnect: () => void;
  error: string | null;
}

const WalletContext = createContext<WalletContextValue>({
  connected: false,
  connecting: false,
  address: null,
  isDemo: false,
  signingKey: null,
  connect: async () => {},
  connectWithKey: async () => null,
  disconnect: () => {},
  error: null,
});

export function useWalletConnection() {
  return useContext(WalletContext);
}

export function WalletProvider({ children }: { children: React.ReactNode }) {
  const [address, setAddress] = useState<string | null>(null);
  const [isDemo, setIsDemo] = useState(false);
  const [signingKey, setSigningKey] = useState<Keypair | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const connect = useCallback(async () => {
    setError(null);
    setConnecting(true);
    setSigningKey(null);
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

  // Connect by pasting a base58 secret key (no browser extension required).
  // Derives the public address from the key so it must be the user's own wallet.
  const connectWithKey = useCallback(async (secretKey: string): Promise<string | null> => {
    setError(null);
    try {
      const trimmed = secretKey.trim();
      if (!trimmed) {
        setError("Enter a secret key.");
        return null;
      }
      const [{ Keypair: SolKeypair }, { default: bs58 }] = await Promise.all([
        import("@solana/web3.js"),
        import("bs58"),
      ]);
      const decoded = bs58.decode(trimmed);
      if (decoded.length !== 64) {
        setError("Secret key must be 64 bytes (base58).");
        return null;
      }
      const kp = SolKeypair.fromSecretKey(decoded);
      setSigningKey(kp);
      setAddress(kp.publicKey.toBase58());
      setIsDemo(false);
      return kp.publicKey.toBase58();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Invalid secret key.");
      return null;
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
    setSigningKey(null);
    setError(null);
  }, []);

  const value = useMemo(
    () => ({
      connected: !!address,
      connecting,
      address,
      isDemo,
      signingKey,
      connect,
      connectWithKey,
      disconnect,
      error,
    }),
    [address, isDemo, signingKey, connecting, connect, connectWithKey, disconnect, error]
  );

  return <WalletContext.Provider value={value}>{children}</WalletContext.Provider>;
}