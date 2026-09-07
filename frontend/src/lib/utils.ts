import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

const SOLANA_EXPLORER = "https://explorer.solana.com";

export function shortAddress(addr: string | null | undefined, chars = 4): string {
  if (!addr) return "—";
  if (addr.length <= chars * 2 + 1) return addr;
  return `${addr.slice(0, chars)}…${addr.slice(-chars)}`;
}

export function formatUsdc(amount: number | null | undefined): string {
  if (amount === null || amount === undefined) return "$0.00";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 6,
    notation: amount >= 100_000 ? "compact" : "standard",
  }).format(amount);
}

export function formatNumber(amount: number | null | undefined, digits = 2): string {
  if (amount === null || amount === undefined) return "—";
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(amount);
}

export function formatSignedUsdc(amount: number, positive: boolean): string {
  return `${positive ? "+" : "−"}${formatUsdc(amount)}`;
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

export function formatTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2, "0")}:${String(
    d.getMinutes()
  ).padStart(2, "0")}:${String(d.getSeconds()).padStart(2, "0")}`;
}

export function timeAgo(iso: string | null | undefined): string {
  if (!iso) return "—";
  const secs = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 1000));
  if (secs < 10) return "just now";
  if (secs < 60) return `${secs}s ago`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function isToday(iso: string | null | undefined): boolean {
  if (!iso) return false;
  const d = new Date(iso);
  const now = new Date();
  return (
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate()
  );
}

export function explorerTxUrl(signature: string, network: "devnet" | "mainnet-beta" = "devnet") {
  return `${SOLANA_EXPLORER}/tx/${signature}?cluster=${network}`;
}

export function explorerAddressUrl(address: string, network: "devnet" | "mainnet-beta" = "devnet") {
  return `${SOLANA_EXPLORER}/address/${address}?cluster=${network}`;
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

export function percentOf(value: number, total: number): number {
  if (total <= 0) return 0;
  return clamp((value / total) * 100, 0, 100);
}