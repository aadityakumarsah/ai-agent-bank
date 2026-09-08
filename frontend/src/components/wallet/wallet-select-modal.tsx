"use client";

import { useEffect, useRef, useState } from "react";
import { X, Loader2, ChevronDown, ChevronUp, KeyRound, Check } from "lucide-react";
import { useWalletConnection } from "./wallet-context";
import type { WalletOptionName } from "./adapters";

/** Primary wallets shown when the list is collapsed. */
const PRIMARY_WALLETS: WalletOptionName[] = ["Solflare", "Phantom"];

/** Extra wallets revealed by "More options". Never faked: each is detected via
 *  its real injected provider; Ledger is hardware-only and can't be detected. */
const EXTRA_WALLETS: WalletOptionName[] = ["Backpack", "Coinbase Wallet", "Ledger"];

const ICON_BG: Record<WalletOptionName, string> = {
  Solflare: "#F5A623",
  Phantom: "#8B76E9",
  Backpack: "#1E5DF0",
  "Coinbase Wallet": "#1652F0",
  Ledger: "#2E3A4D",
};

function WalletIcon({ name, size = 40 }: { name: WalletOptionName; size?: number }) {
  const s = size;
  const letter = name.charAt(0);
  return (
    <span
      className="flex shrink-0 items-center justify-center rounded-[10px] text-white"
      style={{ width: s, height: s, background: ICON_BG[name] }}
      aria-hidden
    >
      <svg width={s * 0.5} height={s * 0.5} viewBox="0 0 24 24" fill="none" stroke="none">
        {name === "Solflare" && (
          <g fill="currentColor">
            <circle cx="12" cy="12" r="3.4" />
            {[0, 45, 90, 135, 180, 225, 270, 315].map((deg) => (
              <line
                key={deg}
                x1="12"
                y1="2.2"
                x2="12"
                y2="5.6"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                transform={`rotate(${deg} 12 12)`}
              />
            ))}
          </g>
        )}
        {name === "Phantom" && (
          <path
            fill="currentColor"
            d="M6.4 4.5h11.2v8.6a4.9 4.9 0 0 1-4.9 4.9h-2.2a4.9 4.9 0 0 1-4.9-4.9V9.2c0-2.6 0-4.7.8-4.7zm2.3 3.6v1.6c0 .6.4 1 1 1s1-.4 1-1V8.1c0-.6-.4-1-1-1s-1 .4-1 1zm5 0v1.6c0 .6.4 1 1 1s1-.4 1-1V8.1c0-.6-.4-1-1-1s-1 .4-1 1z"
          />
        )}
        {name === "Backpack" && (
          <path
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M8.5 9V7.5A3.5 3.5 0 0 1 12 4a3.5 3.5 0 0 1 3.5 3.5V9M6 9.6h12v5.2a4.6 4.6 0 0 1-4.6 4.6h-2.8A4.6 4.6 0 0 1 6 14.8V9.6zM9 12.6h6"
          />
        )}
        {name === "Coinbase Wallet" && (
          <circle cx="12" cy="12" r="8" fill="currentColor" />
        )}
        {name === "Ledger" && (
          <path
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinejoin="round"
            d="M6 3h9a3 3 0 0 1 3 3v12a3 3 0 0 1-3 3H6zM9 8v8"
          />
        )}
      </svg>
    </span>
  );
}

export function WalletSelectModal() {
  const {
    walletSelectOpen,
    closeWalletSelect,
    walletDetection,
    error,
    connectTo,
    connectWithKey,
    onWalletConnected,
  } = useWalletConnection();

  const [expanded, setExpanded] = useState(false);
  const [pending, setPending] = useState<WalletOptionName | null>(null);
  const [keyInput, setKeyInput] = useState("");
  const [keyBusy, setKeyBusy] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);

  const connectWallet = async (name: WalletOptionName) => {
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

  // Escape to close, focus trap while open, block scroll behind the modal.
  useEffect(() => {
    if (!walletSelectOpen) return;
    const card = cardRef.current;
    if (card) {
      card.querySelector<HTMLElement>("[data-wallet-row]")?.focus();
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        closeWalletSelect();
        return;
      }
      if (e.key !== "Tab" || !card) return;
      const focusables = Array.from(
        card.querySelectorAll<HTMLElement>("button, [href], input")
      ).filter((el) => !el.hasAttribute("disabled"));
      if (!focusables.length) return;
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      const active = document.activeElement as HTMLElement | null;
      if (e.shiftKey && (active === first || active === card || !card.contains(active))) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && (active === last || !card.contains(active))) {
        e.preventDefault();
        first.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [walletSelectOpen, closeWalletSelect]);

  if (!walletSelectOpen) return null;

  const allWallets = expanded ? [...PRIMARY_WALLETS, ...EXTRA_WALLETS] : PRIMARY_WALLETS;

  return (
    <div
      className="fixed inset-0 z-[110] flex items-center justify-center p-4 sm:px-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="wallet-select-title"
    >
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-fade-in"
        onClick={closeWalletSelect}
        aria-hidden
      />

      <div
        ref={cardRef}
        className="relative w-[445px] max-w-full rounded-xl border border-white/10 bg-[#0C1524] p-7 shadow-[0_24px_70px_-16px_rgba(0,0,0,0.85)] animate-scale-in"
      >
        <button
          type="button"
          onClick={closeWalletSelect}
          aria-label="Close"
          className="absolute right-4 top-4 flex h-[42px] w-[42px] items-center justify-center rounded-full bg-[#1B2640] text-slate-300 transition-colors hover:bg-[#263350] hover:text-white"
        >
          <X className="h-5 w-5" />
        </button>

        <h2
          id="wallet-select-title"
          className="whitespace-pre-line pr-4 text-[28px] font-bold leading-[1.35] tracking-tight text-white"
        >
          {`Connect a wallet on\nSolana to continue`}
        </h2>

        {error && (
          <p className="mt-6 rounded-md border border-red-400/25 bg-red-500/10 px-3 py-2 text-xs leading-relaxed text-red-300">
            {error}
          </p>
        )}

        <div className="mt-11 flex flex-col gap-3">
          {allWallets.map((name) => {
            const detected = walletDetection[name] === true;
            const busy = pending === name;
            const disabled = !!pending && !busy;
            return (
              <button
                key={name}
                type="button"
                data-wallet-row
                disabled={disabled}
                onClick={() => void connectWallet(name)}
                aria-label={`Connect ${name} wallet`}
                className="flex h-[52px] w-full cursor-pointer items-center gap-3 rounded-lg border border-white/10 bg-white/[0.03] px-3 text-left transition-colors hover:bg-white/[0.08] disabled:cursor-default disabled:opacity-60"
              >
                <WalletIcon name={name} />
                <span className="flex-1 text-[15px] font-medium text-white">{name}</span>
                {busy ? (
                  <Loader2 className="h-4 w-4 animate-spin text-slate-300" />
                ) : detected ? (
                  <span className="inline-flex items-center rounded-full bg-emerald-400/15 px-2 py-0.5 text-[11px] font-medium text-emerald-300">
                    Detected
                  </span>
                ) : null}
              </button>
            );
          })}
        </div>

        {expanded && (
          <div className="mt-6 border-t border-white/10 pt-4">
            <p className="mb-3 text-xs text-slate-400">No extension? Connect directly with a key.</p>
            <div className="flex items-center gap-2">
              <input
                type="password"
                value={keyInput}
                onChange={(e) => setKeyInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") void submitKey();
                }}
                placeholder="base58 secret key"
                autoComplete="off"
                className="h-10 w-full rounded-lg border border-white/10 bg-white/[0.04] px-3 font-mono text-xs text-white outline-none transition-colors placeholder:text-slate-500 focus:border-emerald-400/40"
              />
              <button
                type="button"
                onClick={() => void submitKey()}
                disabled={keyBusy || !keyInput.trim()}
                className="inline-flex h-10 shrink-0 items-center gap-1.5 rounded-lg bg-emerald-500/90 px-3 text-xs font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
              >
                {keyBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                Connect
              </button>
            </div>
          </div>
        )}

        <div className="mt-8 flex items-center justify-end">
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            aria-expanded={expanded}
            className="inline-flex items-center gap-1 text-xs font-medium text-slate-400 transition-colors hover:text-white"
          >
            {expanded ? (
              <>
                Less options
                <ChevronUp className="h-3.5 w-3.5" />
              </>
            ) : (
              <>
                More options
                <ChevronDown className="h-3.5 w-3.5" />
              </>
            )}
          </button>
        </div>

        <p className="mt-6 text-center text-[11px] leading-relaxed text-slate-500">
          Selecting a wallet opens its own approval popup — approve to connect,{" "}
          <span className="inline-flex items-center gap-0.5 align-middle">
            <KeyRound className="h-3 w-3" />
          </span>{" "}
          like signing in with Google. We only receive your public address, never your keys.
        </p>
      </div>
    </div>
  );
}