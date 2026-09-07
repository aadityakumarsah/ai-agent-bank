/**
 * Browser-side Solana helpers for AI Agent Bank frontend.
 *
 * Only PUBLIC data is handled here: RPC urls, token mints and on-chain reads.
 * Secret keys never appear in the browser.
 */
import {
  Connection,
  PublicKey,
  Transaction,
  LAMPORTS_PER_SOL,
} from "@solana/web3.js";
import {
  createTransferCheckedInstruction,
  getAssociatedTokenAddress,
  TOKEN_PROGRAM_ID,
} from "@solana/spl-token";

export const DEVNET_USDC_MINT = "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU";
export const MAINNET_USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v";
export const USDC_DECIMALS = 6;

const DEVNET_RPC = "https://api.devnet.solana.com";

export type SolanaNetwork = "devnet" | "mainnet-beta";

export function getNetwork(): SolanaNetwork {
  const net = (process.env.NEXT_PUBLIC_SOLANA_NETWORK || "devnet").toLowerCase();
  return net === "mainnet" || net === "mainnet-beta" ? "mainnet-beta" : "devnet";
}

/** Public USDC SPL mint for the active network. Configured, not hardcoded in logic. */
export function getUsdcMint(): string {
  return (
    process.env.NEXT_PUBLIC_SOLANA_USDC_MINT ||
    (getNetwork() === "mainnet-beta" ? MAINNET_USDC_MINT : DEVNET_USDC_MINT)
  );
}

export function getRpcUrl(): string {
  return process.env.NEXT_PUBLIC_SOLANA_RPC_URL || DEVNET_RPC;
}

export function getConnection(): Connection {
  return new Connection(getRpcUrl(), "confirmed");
}

/**
 * Mock/simulated signatures (produced by the backend MOCK MODE) start with
 * "mock_". These must NEVER render an explorer link — there is no on-chain tx.
 */
export function isSimulatedSignature(signature?: string | null): boolean {
  return !signature || signature.startsWith("mock_");
}

/** Explorer URL for a real on-chain signature on the active network. */
export function explorerUrlForSignature(signature: string): string {
  const cluster = getNetwork() === "mainnet-beta" ? "mainnet-beta" : "devnet";
  return `https://explorer.solana.com/tx/${signature}?cluster=${cluster}`;
}

export interface WalletBalances {
  sol: number;
  usdc: number;
  lamports: number;
  mint: string;
  network: SolanaNetwork;
}

/** Read the connected wallet's SOL and USDC balances from Solana. */
export async function getWalletBalances(address: string): Promise<WalletBalances> {
  const connection = getConnection();
  const pubkey = new PublicKey(address);
  const mint = new PublicKey(getUsdcMint());
  const lamports = await connection.getBalance(pubkey);
  let usdc = 0;
  try {
    const accounts = await connection.getParsedTokenAccountsByOwner(pubkey, { mint });
    for (const { account } of accounts.value) {
      const amount = account.data.parsed.info?.tokenAmount?.uiAmount;
      if (typeof amount === "number") usdc += amount;
    }
  } catch {
    // token account query can fail; balances just read as 0
  }
  return { sol: lamports / LAMPORTS_PER_SOL, usdc, lamports, mint: getUsdcMint(), network: getNetwork() };
}

/**
 * Build + sign + submit a USDC SPL transfer from the connected wallet
 * (window.solana) to an escrow ATA. Returns the on-chain signature.
 *
 * Used only in REAL MODE with a real wallet (Phantom etc.). The demo wallet
 * cannot sign, so this throws a clear error in that case.
 */
export async function signAndSendUsdcTransfer(opts: {
  from: string;
  to: string;
  amount: number;
  mint?: string;
}): Promise<string> {
  const connection = getConnection();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const wallet = (window as any).solana;
  if (!wallet || typeof wallet.signTransaction !== "function") {
    throw new Error(
      "REAL MODE requires a Solana wallet that can sign transactions (e.g. Phantom)."
    );
  }

  const owner = new PublicKey(opts.from);
  const recipient = new PublicKey(opts.to);
  const mintPubkey = new PublicKey(opts.mint || getUsdcMint());
  const decimals = USDC_DECIMALS;

  const fromAta = await getAssociatedTokenAddress(mintPubkey, owner);
  const toAta = await getAssociatedTokenAddress(mintPubkey, recipient);

  const { blockhash, lastValidBlockHeight } = await connection.getLatestBlockhash();
  const tx = new Transaction({ feePayer: owner, blockhash, lastValidBlockHeight });
  tx.add(
    createTransferCheckedInstruction(
      fromAta,
      mintPubkey,
      toAta,
      owner,
      Math.round(opts.amount * 10 ** decimals),
      decimals,
      [],
      TOKEN_PROGRAM_ID
    )
  );

  const signed = await wallet.signTransaction(tx);
  const signature = await connection.sendRawTransaction(signed.serialize(), {
    skipPreflight: false,
  });
  await connection.confirmTransaction({ signature, blockhash, lastValidBlockHeight });
  return signature;
}