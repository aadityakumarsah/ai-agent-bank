"use client";

import { Wallet, Loader2, Copy, Check, LogOut, KeyRound, X } from "lucide-react";
import { useWalletConnection } from "./wallet-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { shortAddress } from "@/lib/utils";
import { getWalletBalances } from "@/lib/solana";
import { useEffect, useState } from "react";

export function WalletConnectButton({ compact }: { compact?: boolean }) {
  const { connected, connecting, address, walletType, connect, connectWithKey, disconnect, error } =
    useWalletConnection();
  const [copied, setCopied] = useState(false);
  const [sol, setSol] = useState<number | null>(null);
  const [usdc, setUsdc] = useState<number | null>(null);
  const [showKeyInput, setShowKeyInput] = useState(false);
  const [keyInput, setKeyInput] = useState("");
  const [keyBusy, setKeyBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    if (connected && address) {
      setSol(null);
      setUsdc(null);
      getWalletBalances(address)
        .then((b) => {
          if (!cancelled) {
            setSol(b.sol);
            setUsdc(b.usdc);
          }
        })
        .catch(() => {
          if (!cancelled) {
            setSol(null);
            setUsdc(null);
          }
        });
    }
    return () => {
      cancelled = true;
    };
  }, [connected, address]);

  const submitKey = async () => {
    if (!keyInput.trim()) return;
    setKeyBusy(true);
    await connectWithKey(keyInput);
    setKeyBusy(false);
    if (connected) {
      setKeyInput("");
      setShowKeyInput(false);
    }
  };

  if (!connected) {
    return (
      <div className="flex flex-col items-end gap-2">
        {error && <span className="text-xs text-destructive">{error}</span>}
        <div className="flex items-center gap-2">
          <Button size={compact ? "sm" : "default"} onClick={connect} disabled={connecting}>
            {connecting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Wallet className="h-4 w-4" />
            )}
            {connecting ? "Connecting…" : compact ? "Connect" : "Connect Wallet"}
          </Button>
          <Button
            size={compact ? "sm" : "default"}
            variant="outline"
            onClick={() => setShowKeyInput((v) => !v)}
            title="Connect using a pasted secret key"
          >
            <KeyRound className="h-4 w-4" />
            {!compact && "Paste Key"}
          </Button>
        </div>
        {showKeyInput && (
          <div className="flex w-full min-w-[280px] items-center gap-2 rounded-lg border border-border bg-card p-2">
            <Input
              type="password"
              placeholder="base58 secret key"
              value={keyInput}
              onChange={(e) => setKeyInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") void submitKey();
              }}
              className="h-8 font-mono text-xs"
              autoFocus
            />
            <Button size="sm" onClick={() => void submitKey()} disabled={keyBusy}>
              {keyBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Connect"}
            </Button>
            <Button size="icon" variant="ghost" className="h-8 w-8" onClick={() => setShowKeyInput(false)}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        )}
      </div>
    );
  }

  const copy = () => {
    if (!address) return;
    navigator.clipboard?.writeText(address);
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
  };

  return (
    <div className="flex items-center gap-1.5">
      {walletType && !compact && (
        <span
          className="inline-flex items-center rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-primary"
          title="Connected wallet type"
        >
          {walletType}
        </span>
      )}
      {connected && !compact && (
        <div className="hidden items-center gap-1.5 md:flex">
          <span
            className="inline-flex h-8 items-center gap-1 rounded-md border border-border bg-card px-2 text-[11px] tabular-nums text-muted-foreground"
            title="SOL balance"
          >
            {sol === null ? "—" : `${sol.toFixed(2)} SOL`}
          </span>
          <span
            className="inline-flex h-8 items-center gap-1 rounded-md border border-border bg-card px-2 text-[11px] tabular-nums text-muted-foreground"
            title="USDC balance"
          >
            {usdc === null ? "—" : `$${usdc.toLocaleString(undefined, { maximumFractionDigits: 2 })}`}
          </span>
        </div>
      )}
      <button
        onClick={copy}
        className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-card px-2.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
        title={address || undefined}
      >
        {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
        <span className="font-mono">{shortAddress(address, compact ? 4 : 5)}</span>
      </button>
      <Button
        variant="ghost"
        size="icon"
        className="h-8 w-8"
        onClick={disconnect}
        title="Disconnect"
      >
        <LogOut className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
}