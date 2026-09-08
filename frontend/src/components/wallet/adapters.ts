export interface ConnectedWallet {
  publicKey: { toBase58(): string };
  /** Human-readable wallet type, e.g. "Solflare", "Phantom" or "Browser wallet". */
  providerName: string;
}

type WalletProvider = {
  isPhantom?: boolean;
  isSolflare?: boolean;
  isBackpack?: boolean;
  isCoinbaseWallet?: boolean;
  connect: () => Promise<{ publicKey: { toBase58(): string } | undefined }>;
};

export type WalletOptionName =
  | "Solflare"
  | "Phantom"
  | "Backpack"
  | "Coinbase Wallet"
  | "Ledger";

interface DetectedWallet {
  name: WalletOptionName;
  detected: boolean;
  provider: WalletProvider | null;
}

const SOLFLARE_PROVIDER = "solflare";
const PHANTOM_PROVIDER = "phantom";
const BACKPACK_PROVIDER = "backpack";
const COINBASE_PROVIDER = "coinbaseSolana";

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
  if (provider.isBackpack === true) return "Backpack";
  if (provider.isCoinbaseWallet === true) return "Coinbase Wallet";
  return "Browser wallet";
}

function readSolflare(): WalletProvider | null {
  return (
    providerFromGlobal(SOLFLARE_PROVIDER) ??
    (providerFromGlobal("solana")?.isSolflare === true
      ? providerFromGlobal("solana")
      : null)
  );
}

function providerFromNested(key: string, subkey: string): WalletProvider | null {
  const w = window as unknown as Record<string, Record<string, unknown> | undefined>;
  const candidate = w[key]?.[subkey] as WalletProvider | undefined;
  if (
    candidate &&
    typeof candidate === "object" &&
    typeof candidate.connect === "function"
  ) {
    return candidate;
  }
  return null;
}

function readPhantom(): WalletProvider | null {
  const direct = providerFromGlobal(PHANTOM_PROVIDER);
  const nested = providerFromNested(PHANTOM_PROVIDER, "solana");
  const solana = providerFromGlobal("solana");
  if (direct && direct.isPhantom !== false) return direct;
  if (nested) return nested;
  if (solana && solana.isPhantom === true) return solana;
  return null;
}

function readBackpack(): WalletProvider | null {
  const direct = providerFromGlobal(BACKPACK_PROVIDER);
  const solana = providerFromGlobal("solana");
  if (direct && direct.isBackpack !== false) return direct;
  if (solana && solana.isBackpack === true) return solana;
  return null;
}

function readCoinbase(): WalletProvider | null {
  const direct = providerFromGlobal(COINBASE_PROVIDER);
  const solana = providerFromGlobal("solana");
  if (direct && direct.isCoinbaseWallet !== false) return direct;
  if (solana && solana.isCoinbaseWallet === true) return solana;
  return null;
}

function providerFor(name: WalletOptionName): (() => WalletProvider | null) | null {
  switch (name) {
    case "Solflare":
      return readSolflare;
    case "Phantom":
      return readPhantom;
    case "Backpack":
      return readBackpack;
    case "Coinbase Wallet":
      return readCoinbase;
    case "Ledger":
      // Ledger has no injected browser provider; it is hardware-only (via a
      // wallet adapter / Solflare). Always reported as not detected.
      return null;
  }
}

/**
 * Returns each supported wallet and whether its extension is present.
 * Used to render the chooser ("Solflare — Detected") instead of silently
 * auto-picking one. Waits for delayed injection before reporting absence.
 */
export async function detectWallets(): Promise<DetectedWallet[]> {
  const names: WalletOptionName[] = [
    "Solflare",
    "Phantom",
    "Backpack",
    "Coinbase Wallet",
    "Ledger",
  ];
  const results = await Promise.all(
    names.map(async (name) => {
      const read = providerFor(name);
      const provider = read ? await waitForGlobal(read) : null;
      return { name, detected: !!provider, provider };
    })
  );
  return results;
}

async function runConnect(
  provider: WalletProvider,
  fallbackName: string
): Promise<ConnectedWallet | null> {
  try {
    const res = await provider.connect();
    if (!res?.publicKey) return null;
    const actual = nameOf(provider);
    return {
      publicKey: res.publicKey,
      providerName: actual === "Browser wallet" ? fallbackName : actual,
    };
  } catch {
    return null;
  }
}

/** Connect through a specific wallet extension chosen by the user. */
export async function connectTo(name: WalletOptionName): Promise<ConnectedWallet | null> {
  // Poll for the specific extension first.
  const read = providerFor(name);
  if (!read) return null; // e.g. Ledger — not connectable via injection
  const picked = await waitForGlobal(read, 3000);
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
  for (const key of [
    SOLFLARE_PROVIDER,
    PHANTOM_PROVIDER,
    BACKPACK_PROVIDER,
    COINBASE_PROVIDER,
    "solana",
    "phantom",
  ]) {
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