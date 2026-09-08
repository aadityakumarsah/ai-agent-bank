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

const SOLFLARE_PROVIDER = "solflare";
const PHANTOM_PROVIDER = "phantom";

function pickProvider(): { provider: WalletProvider; name: string } | null {
  const w = window as unknown as Record<string, unknown> & { solana?: WalletProvider };
  // Solflare browser extension injects its own global (and also mirrors
  // window.solana). Prefer the dedicated global so a Solflare user isn't
  // grabbed by the generic path.
  if (
    typeof w[SOLFLARE_PROVIDER] === "object" &&
    w[SOLFLARE_PROVIDER] !== null &&
    typeof (w[SOLFLARE_PROVIDER] as WalletProvider).connect === "function"
  ) {
    return { provider: w[SOLFLARE_PROVIDER] as WalletProvider, name: "Solflare" };
  }
  // Generic injected provider (Phantom, or Solflare exposing window.solana).
  const solana = w.solana;
  if (
    solana &&
    typeof solana.connect === "function" &&
    (solana.isPhantom === true || solana.isSolflare === true)
  ) {
    return { provider: solana, name: solana.isPhantom === true ? "Phantom" : "Solflare" };
  }
  return null;
}

export async function tryConnect(): Promise<ConnectedWallet | null> {
  const picked = pickProvider();
  if (!picked) return null;

  return picked.provider
    .connect()
    .then((res) => {
      if (!res?.publicKey) return null;
      return { publicKey: res.publicKey, providerName: picked.name };
    })
    .catch(() => null);
}

export async function tryDisconnect(): Promise<void> {
  const picked = pickProvider();
  if (picked && typeof (picked.provider as WalletProvider & { disconnect?: () => unknown }).disconnect === "function") {
    try {
      (picked.provider as WalletProvider & { disconnect: () => unknown }).disconnect();
    } catch {
      /* ignore */
    }
  }
  return Promise.resolve();
}