"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Keypair } from "@solana/web3.js";
import { WalletSelectModal } from "./wallet-select-modal";
import type { WalletOptionName } from "./adapters";

export type WalletType =
  | WalletOptionName
  | "Imported key"
  | "Browser wallet";

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
  connectTo: (name: WalletOptionName) => Promise<boolean>;
  connectWithKey: (secretKey: string) => Promise<string | null>;
  disconnect: () => void;
  error: string | null;
  /** Wallet chooser modal (shown by every "Connect wallet" button). */
  walletSelectOpen: boolean;
  openWalletSelect: (onConnected?: () => void) => void;
  closeWalletSelect: () => void;
  /** Availability of each wallet extension, shown as "Detected" badges. */
  walletDetection: Partial<Record<WalletOptionName, boolean>>;
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
  walletDetection: {},
  onWalletConnected: () => {},
});

// The wallet session (address + type + optional imported secret key) is kept
// in localStorage so a page refresh restores the connection instead of forcing
// the user to reconnect. The imported secret key is stored because that mode's
// whole point is the app holding the key — without it a refresh would lose the
// ability to sign.
const SESSION_KEY = "aibank_session";

interface PersistedSession {
  address: string;
  walletType: WalletType;
  importedKey: string | null;
}

function saveSession(session: PersistedSession): void {
  try {
    window.localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  } catch {
    /* ignore */
  }
}

function loadSession(): PersistedSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<PersistedSession>;
    if (typeof parsed.address !== "string") return null;
    return {
      address: parsed.address,
      walletType: (parsed.walletType as WalletType) ?? "Browser wallet",
      importedKey: typeof parsed.importedKey === "string" ? parsed.importedKey : null,
    };
  } catch {
    return null;
  }
}

function clearSession(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(SESSION_KEY);
  } catch {
    /* ignore */
  }
}

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
  const [walletDetection, setWalletDetection] = useState<
    Partial<Record<WalletOptionName, boolean>>
  >({});
  const onConnectedRef = useRef<(() => void) | null>(null);

  const openWalletSelect = useCallback((onConnected?: () => void) => {
    onConnectedRef.current = onConnected ?? null;
    setError(null);
    // Detect which extensions are installed so the chooser can badge them.
    // detectWallets() polls briefly because extensions inject after load.
    import("@/components/wallet/adapters")
      .then(({ detectWallets }) => detectWallets())
      .then((wallets) => {
        setWalletDetection(
          Object.fromEntries(wallets.map((w) => [w.name, w.detected]))
        );
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
      saveSession({
        address: adapter.publicKey.toBase58(),
        walletType: adapter.providerName as WalletType,
        importedKey: null,
      });
      // Establish server-side identity: nonce -> sign -> JWT (Bearer token).
      const { authenticateWallet } = await import("@/lib/auth");
      const outcome = await authenticateWallet(adapter);
      if (!outcome.ok && outcome.error) {
        setError(outcome.error);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to connect wallet");
    } finally {
      setConnecting(false);
    }
  }, []);

  // Connect through a wallet the user explicitly chose in the modal.
  const connectTo = useCallback(
    async (name: WalletOptionName): Promise<boolean> => {
      setError(null);
      setConnecting(true);
      setSigningKey(null);
      try {
        const { connectTo: runConnect } = await import("@/components/wallet/adapters");
        const outcome = await runConnect(name);
        if (!outcome.ok) {
          if (outcome.reason === "not_detected") {
            setError(
              `${name} wasn't detected on this page. Make sure the ${name} extension is installed and enabled, then reload this page and try again.`
            );
          } else {
            setError(
              `Couldn't connect to ${name}. If a ${name} popup appeared, approve it — or if you've already connected before, disconnect and reconnect.`
            );
          }
          return false;
        }
        if (!outcome.wallet?.publicKey) {
          setError(`Couldn't connect to ${name}.`);
          return false;
        }
        setAddress(outcome.wallet.publicKey.toBase58());
        setWalletType(outcome.wallet.providerName as WalletType);
        setIsDemo(false);
        saveSession({
          address: outcome.wallet.publicKey.toBase58(),
          walletType: outcome.wallet.providerName as WalletType,
          importedKey: null,
        });
        // Establish server-side identity so REQUIRE_AUTH routes authenticate.
        const { authenticateWallet } = await import("@/lib/auth");
        const authorized = await authenticateWallet(outcome.wallet);
        if (!authorized.ok && authorized.error) {
          setError(authorized.error);
          return false;
        }
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
      const keyAddress = kp.publicKey.toBase58();
      saveSession({ address: keyAddress, walletType: "Imported key", importedKey: trimmed });
      // Sign the auth nonce with the imported key directly (no wallet popup).
      const { authenticateWithKeypair } = await import("@/lib/auth");
      const outcome = await authenticateWithKeypair(kp);
      if (!outcome.ok && outcome.error) {
        setError(outcome.error);
        return null;
      }
      return keyAddress;
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
    const { clearAuthToken } = await import("@/lib/auth");
    clearAuthToken();
    clearSession();
    setAddress(null);
    setWalletType(null);
    setIsDemo(false);
    setSigningKey(null);
    setError(null);
  }, []);

  // On page load, restore a previously saved wallet session so a refresh does
  // not force the user to reconnect. The JWT (8-day expiry) is reused silently;
  // a keypair session re-derives the key and issues a fresh token locally.
  const restoreSession = useCallback(async () => {
    const saved = loadSession();
    if (!saved) return;

    if (saved.importedKey) {
      try {
        const [{ Keypair: SolKeypair }, { default: bs58 }] = await Promise.all([
          import("@solana/web3.js"),
          import("bs58"),
        ]);
        const kp = SolKeypair.fromSecretKey(bs58.decode(saved.importedKey));
        if (kp.publicKey.toBase58() !== saved.address) {
          clearSession();
          return;
        }
        setSigningKey(kp);
        setAddress(saved.address);
        setWalletType(saved.walletType);
        setIsDemo(false);
        const { authenticateWithKeypair } = await import("@/lib/auth");
        const outcome = await authenticateWithKeypair(kp);
        if (!outcome.ok && outcome.error) setError(outcome.error);
      } catch {
        setError("Couldn't restore your imported wallet session.");
        clearSession();
      }
      return;
    }

    setAddress(saved.address);
    setWalletType(saved.walletType);
    setIsDemo(false);
    const { getAuthToken } = await import("@/lib/auth");
    if (getAuthToken()) return;
    try {
      const { tryConnect } = await import("@/components/wallet/adapters");
      const adapter = await tryConnect();
      if (adapter?.publicKey?.toBase58() === saved.address) {
        const { authenticateWallet } = await import("@/lib/auth");
        const outcome = await authenticateWallet(adapter);
        if (!outcome.ok && outcome.error) setError(outcome.error);
      }
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    void restoreSession();
  }, [restoreSession]);

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
      walletDetection,
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
      walletDetection,
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