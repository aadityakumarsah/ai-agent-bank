import bs58 from "bs58";
import { Keypair } from "@solana/web3.js";
import { ed25519 } from "@noble/curves/ed25519";
import { API_BASE, API_V1 } from "@/lib/api-config";
import type { ConnectedWallet } from "@/components/wallet/adapters";

const AUTH_TOKEN_KEY = "aibank_auth_token";

export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(AUTH_TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setAuthToken(token: string | null): void {
  if (typeof window === "undefined") return;
  try {
    if (token) window.localStorage.setItem(AUTH_TOKEN_KEY, token);
    else window.localStorage.removeItem(AUTH_TOKEN_KEY);
  } catch {
    /* ignore */
  }
}

export function clearAuthToken(): void {
  setAuthToken(null);
}

/** Encode raw signature bytes as the base58 string the API expects. */
export function encodeSignature(bytes: Uint8Array): string {
  return bs58.encode(bytes);
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${API_V1}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail: string = res.statusText;
    try {
      const b = await res.json();
      detail = typeof b.detail === "string" ? b.detail : JSON.stringify(b.detail ?? b);
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export interface AuthOutcome {
  ok: boolean;
  token: string | null;
  error?: string;
}

/**
 * Authenticate this browser session as a specific wallet via the standard
 * one-time-nonce flow: the wallet signs the server message, the backend
 * verifies the Ed25519 signature and returns a JWT.
 *
 * The JWT is stored locally and attached to every API call as a Bearer header,
 * which is what makes REQUIRE_AUTH=true on the backend enforceable.
 */
export async function authenticateWallet(wallet: ConnectedWallet): Promise<AuthOutcome> {
  const walletAddress = wallet.publicKey.toBase58();
  try {
    if (typeof wallet.signMessage !== "function") {
      return {
        ok: false,
        token: null,
        error:
          "This wallet connection doesn't expose message signing, so server-side identity can't be proven.",
      };
    }
    const nonce = await postJson<{ wallet_address: string; nonce: string; message: string }>(
      "/auth/nonce",
      { wallet_address: walletAddress }
    );
    const bytes = new TextEncoder().encode(nonce.message);
    const signature = encodeSignature(await wallet.signMessage(bytes));
    const verified = await postJson<{ access_token: string; wallet_address: string }>(
      "/auth/verify",
      { wallet_address: walletAddress, message: nonce.message, signature }
    );
    setAuthToken(verified.access_token);
    return { ok: true, token: verified.access_token };
  } catch (e) {
    const message = e instanceof Error ? e.message : "Authentication failed";
    return { ok: false, token: null, error: message };
  }
}

/**
 * Authenticate with a locally-imported keypair (no browser extension popup).
 * Signing happens in the browser with the pasted secret key.
 */
export async function authenticateWithKeypair(keypair: Keypair): Promise<AuthOutcome> {
  const walletAddress = keypair.publicKey.toBase58();
  try {
    const nonce = await postJson<{ wallet_address: string; nonce: string; message: string }>(
      "/auth/nonce",
      { wallet_address: walletAddress }
    );
    const bytes = new TextEncoder().encode(nonce.message);
    // Solana's Keypair doesn't expose a public sign method, so sign the
    // nonce with the ed25519 seed (bytes 0..32) via @noble/curves.
    const seed = keypair.secretKey.slice(0, 32);
    const signature = encodeSignature(ed25519.sign(bytes, seed));
    const verified = await postJson<{ access_token: string; wallet_address: string }>(
      "/auth/verify",
      { wallet_address: walletAddress, message: nonce.message, signature }
    );
    setAuthToken(verified.access_token);
    return { ok: true, token: verified.access_token };
  } catch (e) {
    const message = e instanceof Error ? e.message : "Authentication failed";
    return { ok: false, token: null, error: message };
  }
}