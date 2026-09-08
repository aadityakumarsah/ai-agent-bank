export interface ConnectedWallet {
  publicKey: { toBase58(): string };
  /** Human-readable wallet type, e.g. "Solflare", "Phantom" or "Browser wallet". */
  providerName: string;
}

type WalletProvider = {
  isPhantom?: boolean;
  isSolflare?: boolean;
  connect: () => Promise<{ publicKey: { toBase58(): string } | undefined }>;
};

export type WalletOptionName = "Solflare" | "Phantom";

interface DetectedWallet {
  name: WalletOptionName;
  detected: boolean;
  provider: WalletProvider | null;
}

const SOLFLARE_PROVIDER = "solflare";
const PHANTOM_PROVIDER = "phantom";

function providerFromGlobal(key: string): WalletProvider | null {
  const w = window as unknown as Record<string, unknown>;
  const candidate = w[key] as WalletProvider | undefined;
  if (
    candidate &&
    typeof candidate === "object" &&
    typeof candidate.connect === "function"
  ) {
    return candidate;
  }
  return null;
}

/**
 * Returns each supported wallet and whether its browser extension is present.
 * Used to render the chooser ("Solflare — Detected") instead of silently
 * auto-picking one.
 */
export function detectWallets(): DetectedWallet[] {
  const solana = providerFromGlobal("solana");
  const solflareDirect = providerFromGlobal(SOLFLARE_PROVIDER);
  const phantom = providerFromGlobal("phantom");

  const solflareProvider =
    solflareDirect && (solflareDirect.isSolflare !== false)
      ? solflareDirect
      : solana && solana.isSolflare === true
        ? solana
        : null;

  const phantomProvider =
    phantom && phantom.isPhantom !== false
      ? phantom
      : solana && solana.isPhantom === true
        ? solana
        : null;

  return [
    { name: "Solflare", detected: !!solflareProvider, provider: solflareProvider },
    { name: "Phantom", detected: !!phantomProvider, provider: phantomProvider },
  ];
}

/** Connect through a specific wallet extension chosen by the user. */
export async function connectTo(name: WalletOptionName): Promise<ConnectedWallet | null> {
  const wallet = detectWallets().find((w) => w.name === name);
  const picked = wallet?.detected ? wallet.provider : null;
  if (!picked) return null;

  return picked
    .connect()
    .then((res) => {
      if (!res?.publicKey) return null;
      return { publicKey: res.publicKey, providerName: name };
    })
    .catch(() => null);
}

export async function tryConnect(): Promise<ConnectedWallet | null> {
  const wallets = detectWallets();
  const first = wallets.find((w) => w.detected);
  const picked = first?.provider ?? null;
  if (!picked) return null;

  return picked
    .connect()
    .then((res) => {
      if (!res?.publicKey) return null;
      return { publicKey: res.publicKey, providerName: first!.name };
    })
    .catch(() => null);
}

export async function tryDisconnect(): Promise<void> {
  for (const wallet of detectWallets()) {
    const provider = wallet.provider as (WalletProvider & { disconnect?: () => unknown }) | null;
    if (provider && typeof provider.disconnect === "function") {
      try {
        provider.disconnect();
      } catch {
        /* ignore */
      }
    }
  }
  return Promise.resolve();
}