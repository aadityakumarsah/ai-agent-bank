type WalletProvider = {
  isPhantom?: boolean;
  isSolflare?: boolean;
  connect: () => Promise<{ publicKey: { toBase58(): string } | undefined }>;
};

const SOLFLARE_PROVIDER = "solflare";
const PHANTOM_PROVIDER = "phantom";

function pickProvider(): WalletProvider | null {
  const w = window as unknown as Record<string, unknown> & { solana?: WalletProvider };
  // Solflare browser extension injects its own global (and also mirrors
  // window.solana). Prefer the dedicated global so a Solflare user isn't
  // grabbed by the generic path.
  if (
    typeof w[SOLFLARE_PROVIDER] === "object" &&
    w[SOLFLARE_PROVIDER] !== null &&
    typeof (w[SOLFLARE_PROVIDER] as WalletProvider).connect === "function"
  ) {
    return w[SOLFLARE_PROVIDER] as WalletProvider;
  }
  // Generic injected provider (Phantom, or Solflare exposing window.solana).
  const solana = w.solana;
  if (
    solana &&
    typeof solana.connect === "function" &&
    (solana.isPhantom === true || solana.isSolflare === true)
  ) {
    return solana;
  }
  return null;
}

export function tryConnect(): Promise<{
  publicKey: { toBase58(): string };
} | null> {
  const provider = pickProvider();
  if (!provider) return Promise.resolve(null);

  return provider
    .connect()
    .then((res) => {
      if (!res?.publicKey) return null;
      return { publicKey: res.publicKey };
    })
    .catch(() => null);
}

export function tryDisconnect(): Promise<void> {
  const provider = pickProvider();
  if (provider && typeof (provider as WalletProvider & { disconnect?: () => unknown }).disconnect === "function") {
    try {
      (provider as WalletProvider & { disconnect: () => unknown }).disconnect();
    } catch {
      /* ignore */
    }
  }
  return Promise.resolve();
}