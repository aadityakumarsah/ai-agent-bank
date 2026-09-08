"use client";

import React, { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";
import { Keypair } from "@solana/web3.js";
import { WalletSelectModal } from "./wallet-select-modal";

export type WalletType = "Solflare" | "Phantom" | "Imported key" | "Browser wallet";

interface WalletContextValue {
  connected: boolean;
  connecting: boolean;
  address: string | null;
  /** Human-readable wallet type shown to the user (e.g. Solflare / Phantom). */
  walletType: WalletType | null;
  /** False always on the real flow — there is no simulated wallet anymore. */
  isDemo: boolean;
  signingKey: Keypair | null;
  connect: () => Promise<void>;
  connectTo: (name: "Solflare" | "Phantom") => Promise<boolean>;
  connectWithKey: (secretKey: string) => Promise<string | null>;
  disconnect: () => void;
  error: string | null;
  /** Wallet chooser modal (shown by every "Connect wallet" button). */
  walletSelectOpen: boolean;
  openWalletSelect: (onConnected?: () => void) => void;
  closeWalletSelect: () => void;
  walletOptions: { name: "Solflare" | "Phantom"; detected: boolean }[];
  /** Run the "on connected" callback registered when the modal was opened. */
  onWalletConnected: () => void;
}

const WalletContext = createContext<WalletContextValue>({
  connected: false,
  connecting: false,
  address: null,
  walletType: null,
  isDemo: false,
  signingKey: null,
  connect: async () => {},
  connectTo: async () => false,
  connectWithKey: async () => null,
  disconnect: () => {},
  error: null,
  walletSelectOpen: false,
  openWalletSelect: () => {},
  closeWalletSelect: () => {},
  walletOptions: [
    { name: "Solflare", detected: false },
    { name: "Phantom", detected: false },
  ],
  onWalletConnected: () => {},
});

export function useWalletConnection() {
  return useContext(WalletContext);
}

export function WalletProvider({ children }: { children: React.ReactNode }) {
  const [address, setAddress] = useState<string | null>(null);
  const [walletType, setWalletType] = useState<WalletType | null>(null);
  const [isDemo, setIsDemo] = useState(false);
  const [signingKey, setSigningKey] = useState<Keypair | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [walletSelectOpen, setWalletSelectOpen] = useState(false);
  const [walletOptions, setWalletOptions] = useState<
    { name: "Solflare" | "Phantom"; detected: boolean }[]
  >([]);
  const onConnectedRef = useRef<(() => void) | null>(null);

  const openWalletSelect = useCallback((onConnected?: () => void) => {
    onConnectedRef.current = onConnected ?? null;
    setError(null);
    // Detect which extensions are installed so the chooser can badge them.
    import("@/components/wallet/adapters").then(({ detectWallets }) => {
      setWalletOptions(detectWallets().map((w) => ({ name: w.name, detected: w.detected })));
    });
    setWalletSelectOpen(true);
  }, []);

  const closeWalletSelect = useCallback(() => {
    setWalletSelectOpen(false);
    onConnectedRef.current = null;
  }, []);

  const onWalletConnected = useCallback(() => {
    onConnectedRef.current?.();
    onConnectedRef.current = null;
    setWalletSelectOpen(false);
  }, []);

  const connect = useCallback(async () => {
    setError(null);
    setConnecting(true);
    setSigningKey(null);
    try {
      // Real Solana wallet adapter only (Solflare / Phantom browser extension).
      // There is no simulated fallback: a real user must have a real wallet.
      const { tryConnect } = await import("@/components/wallet/adapters");
      const adapter = await tryConnect();
      if (!adapter?.publicKey) {
        setError(
          "No Solana wallet found. Install the Solflare or Phantom browser extension, then try again."
        );
        return;
      }
      setAddress(adapter.publicKey.toBase58());
      setWalletType(adapter.providerName as WalletType);
      setIsDemo(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to connect wallet");
    } finally {
      setConnecting(false);
    }
  }, []);

  // Connect through a wallet the user explicitly chose in the modal.
  const connectTo = useCallback(
    async (name: "Solflare" | "Phantom"): Promise<boolean> => {
      setError(null);
      setConnecting(true);
      setSigningKey(null);
      try {
        const { connectTo: runConnect } = await import("@/components/wallet/adapters");
        const adapter = await runConnect(name);
        if (!adapter?.publicKey) {
          setError(
            `${name} was not detected in this browser. Install the ${name} extension, or pick another wallet.`
          );
          return false;
        }
        setAddress(adapter.publicKey.toBase58());
        setWalletType(adapter.providerName as WalletType);
        setIsDemo(false);
        return true;
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to connect wallet");
        return false;
      } finally {
        setConnecting(false);
      }
    },
    []
  );

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
      setWalletType("Imported key");
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
    setWalletType(null);
    setIsDemo(false);
    setSigningKey(null);
    setError(null);
  }, []);

  const value = useMemo(
    () => ({
      connected: !!address,
      connecting,
      address,
      walletType,
      isDemo,
      signingKey,
      connect,
      connectTo,
      connectWithKey,
      disconnect,
      error,
      walletSelectOpen,
      openWalletSelect,
      closeWalletSelect,
      walletOptions,
      onWalletConnected,
    }),
    [
      address,
      walletType,
      isDemo,
      signingKey,
      connecting,
      connect,
      connectTo,
      connectWithKey,
      disconnect,
      error,
      walletSelectOpen,
      openWalletSelect,
      closeWalletSelect,
      walletOptions,
      onWalletConnected,
    ]
  );

  return (
    <WalletContext.Provider value={value}>
      {children}
      <WalletSelectModal />
    </WalletContext.Provider>
  );
}