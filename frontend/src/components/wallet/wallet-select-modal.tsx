"use client";

import { useState } from "react";
import { Loader2, KeyRound, Check, ChevronDown, ChevronUp } from "lucide-react";
import { Dialog } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useWalletConnection } from "./wallet-context";
import { cn } from "@/lib/utils";

const WALLET_STYLE: Record<"Solflare" | "Phantom", { from: string; to: string; letter: string }> = {
  Solflare: { from: "#F7931A", to: "#E8410C", letter: "S" },
  Phantom: { from: "#A5B4FC", to: "#7C6CF6", letter: "P" },
};

function WalletIcon({ name, className }: { name: "Solflare" | "Phantom"; className?: string }) {
  const s = WALLET_STYLE[name];
  return (
    <span
      className={cn(
        "flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-bold text-white",
        className
      )}
      style={{ background: `linear-gradient(135deg, ${s.from}, ${s.to})` }}
      aria-hidden
    >
      {s.letter}
    </span>
  );
}

export function WalletSelectModal() {
  const {
    walletSelectOpen,
    closeWalletSelect,
    walletOptions,
    error,
    connectTo,
    connectWithKey,
    onWalletConnected,
  } = useWalletConnection();

  const [expanded, setExpanded] = useState(false);
  const [keyInput, setKeyInput] = useState("");
  const [keyBusy, setKeyBusy] = useState(false);
  const [pending, setPending] = useState<"Solflare" | "Phantom" | null>(null);

  const connectWallet = async (name: "Solflare" | "Phantom") => {
    setPending(name);
    const ok = await connectTo(name);
    setPending(null);
    if (ok) onWalletConnected();
  };

  const submitKey = async () => {
    if (!keyInput.trim() || keyBusy) return;
    setKeyBusy(true);
    const addr = await connectWithKey(keyInput);
    setKeyBusy(false);
    if (addr) {
      setKeyInput("");
      onWalletConnected();
    }
  };

  return (
    <Dialog
      open={walletSelectOpen}
      onClose={closeWalletSelect}
      title="Connect your wallet"
      description="Connect a wallet on Solana to continue. Your wallet signs every funding transfer and approval."
    >
      <div className="flex flex-col gap-3">
        {error && (
          <div className="rounded-md border border-destructive/25 bg-destructive/10 px-3 py-2 text-xs text-destructive">
            {error}
          </div>
        )}

        <div className="flex flex-col gap-2">
          {walletOptions.map((wallet) => {
            const busy = pending === wallet.name;
            return (
              <button
                key={wallet.name}
                disabled={!!pending && !busy}
                onClick={() => void connectWallet(wallet.name)}
                className={cn(
                  "group flex w-full items-center gap-3 rounded-lg border border-border bg-card px-3 py-2.5 text-left transition-colors",
                  "hover:border-primary/40 hover:bg-secondary/60 disabled:opacity-60"
                )}
              >
                <WalletIcon name={wallet.name} />
                <span className="flex-1">
                  <span className="block text-sm font-medium text-foreground">{wallet.name}</span>
                  <span className="block text-xs text-muted-foreground">
                    {wallet.detected
                      ? "Browser extension installed"
                      : "Not detected in this browser"}
                  </span>
                </span>
                {busy ? (
                  <Loader2 className="h-4 w-4 animate-spin text-primary" />
                ) : wallet.detected ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-success/15 px-2 py-0.5 text-[10px] font-semibold text-success">
                    Detected
                  </span>
                ) : (
                  <span className="text-xs text-muted-foreground group-hover:text-foreground">
                    Open
                  </span>
                )}
              </button>
            );
          })}
        </div>

        <button
          onClick={() => setExpanded((v) => !v)}
          className="mx-auto inline-flex items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-foreground"
        >
          {expanded ? (
            <>
              <ChevronUp className="h-3.5 w-3.5" /> Less options
            </>
          ) : (
            <>
              <ChevronDown className="h-3.5 w-3.5" /> More options
            </>
          )}
        </button>

        {expanded && (
          <div className="flex flex-col gap-2 rounded-lg border border-border bg-muted/30 p-3">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <KeyRound className="h-3.5 w-3.5 shrink-0" />
              No extension? Paste a 64-byte base58 secret key to connect directly.
            </div>
            <div className="flex items-center gap-2">
              <Input
                type="password"
                placeholder="base58 secret key"
                value={keyInput}
                onChange={(e) => setKeyInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") void submitKey();
                }}
                className="h-9 font-mono text-xs"
                autoComplete="off"
              />
              <Button size="sm" onClick={() => void submitKey()} disabled={keyBusy}>
                {keyBusy ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Check className="h-4 w-4" />
                )}
                Connect
              </Button>
            </div>
          </div>
        )}
      </div>
    </Dialog>
  );
}