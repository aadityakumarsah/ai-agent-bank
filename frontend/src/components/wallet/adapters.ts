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

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/**
 * Browser wallet extensions usually inject their provider a moment AFTER the
 * page finishes loading (not synchronously). Poll for a short window so an
 * installed wallet isn't wrongly reported as "not detected".
 */
async function waitForGlobal(
  read: () => WalletProvider | null,
  timeoutMs = 3000
): Promise<WalletProvider | null> {
  const start = Date.now();
  for (;;) {
    const found = read();
    if (found) return found;
    if (Date.now() - start > timeoutMs) return null;
    await sleep(100);
  }
}

function nameOf(provider: WalletProvider): string {
  if (provider.isPhantom === true) return "Phantom";
  if (provider.isSolflare === true) return "Solflare";
  return "Browser wallet";
}

function solflareCandidates(): WalletProvider | null {
  return (
    providerFromGlobal(SOLFLARE_PROVIDER) ??
    (providerFromGlobal("solana")?.isSolflare === true
      ? providerFromGlobal("solana")
      : null)
  );
}

function phantomCandidates(): WalletProvider | null {
  const phantom = providerFromGlobal(PHANTOM_PROVIDER);
  const phantomSolana = providerFromGlobal("phantom") as WalletProvider | null;
  const solana = providerFromGlobal("solana");
  if (phantom && phantom.isPhantom !== false) return phantom;
  // Newer Phantom versions expose window.phantom.solana.
  if (phantomSolana && typeof phantomSolana.connect === "function") return phantomSolana;
  if (solana && solana.isPhantom === true) return solana;
  return null;
}

/**
 * Returns each supported wallet and whether its extension is present.
 * Used to render the chooser ("Solflare — Detected") instead of silently
 * auto-picking one. Waits for delayed injection before reporting absence.
 */
export async function detectWallets(): Promise<DetectedWallet[]> {
  const solflare = await waitForGlobal(solflareCandidates);
  const phantom = await waitForGlobal(phantomCandidates);
  return [
    { name: "Solflare", detected: !!solflare, provider: solflare },
    { name: "Phantom", detected: !!phantom, provider: phantom },
  ];
}

/** Connect through a specific wallet extension chosen by the user. */
export async function connectTo(name: WalletOptionName): Promise<ConnectedWallet | null> {
  // Poll for the specific extension first.
  const wallet = (await detectWallets()).find((w) => w.name === name);
  const picked = wallet?.detected ? wallet.provider : null;
  if (picked) {
    return runConnect(picked, name);
  }

  // Fallback: any injected Solana provider works for connecting. This keeps
  // the flow working when the extension injects late or only into
  // window.solana without a reliable flag.
  const generic = await waitForGlobal(() => providerFromGlobal("solana"), 1500);
  if (generic) {
    return runConnect(generic, nameOf(generic));
  }
  return null;
}

async function runConnect(
  provider: WalletProvider,
  fallbackName: string
): Promise<ConnectedWallet | null> {
  try {
    const res = await provider.connect();
    if (!res?.publicKey) return null;
    const actual = nameOf(provider);
    return { publicKey: res.publicKey, providerName: actual === "Browser wallet" ? fallbackName : actual };
  } catch {
    return null;
  }
}

export async function tryConnect(): Promise<ConnectedWallet | null> {
  const wallets = await detectWallets();
  const first = wallets.find((w) => w.detected);
  const picked = first?.provider ?? null;
  if (!picked) {
    const generic = await waitForGlobal(() => providerFromGlobal("solana"), 1500);
    return generic ? runConnect(generic, "Browser wallet") : null;
  }
  return runConnect(picked, first!.name);
}

export async function tryDisconnect(): Promise<void> {
  for (const key of [SOLFLARE_PROVIDER, PHANTOM_PROVIDER, "solana", "phantom"]) {
    const provider = providerFromGlobal(key) as
      | (WalletProvider & { disconnect?: () => unknown })
      | null;
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