"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Wallet, Copy, Check, Landmark, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { NAV_ITEMS } from "./nav-items";
import { useApprovals } from "@/components/approvals/approvals-context";
import { useWalletConnection } from "@/components/wallet/wallet-context";
import { useConfigStatus } from "@/hooks/use-config-status";
import { cn, shortAddress } from "@/lib/utils";

function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const { pendingCount } = useApprovals();

  return (
    <nav className="flex flex-1 flex-col gap-0.5 px-3">
      {NAV_ITEMS.map((item) => {
        const active = item.exact
          ? pathname === item.href
          : pathname.startsWith(item.href);
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            className={cn(
              "group flex items-center gap-3 rounded-lg border border-transparent px-3 py-2 text-sm font-medium transition-colors",
              active
                ? "border-border bg-secondary/70 text-foreground"
                : "text-muted-foreground hover:bg-secondary/50 hover:text-foreground"
            )}
          >
            <Icon
              className={cn(
                "h-4 w-4 shrink-0",
                active ? "text-primary" : "text-muted-foreground group-hover:text-foreground"
              )}
            />
            <span className="flex-1">{item.label}</span>
            {item.label === "Approvals" && pendingCount > 0 && (
              <span className="rounded-full bg-primary px-1.5 py-0.5 text-[10px] font-bold tabular-nums text-primary-foreground">
                {pendingCount}
              </span>
            )}
          </Link>
        );
      })}
    </nav>
  );
}

function WalletStatus() {
  const { connected, connecting, address, isDemo, connect, disconnect } = useWalletConnection();
  const [copied, setCopied] = useState(false);

  const copy = () => {
    if (!address) return;
    navigator.clipboard?.writeText(address);
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
  };

  if (!connected) {
    return (
      <button
        onClick={connect}
        disabled={connecting}
        className="flex w-full items-center gap-3 rounded-lg border border-border bg-secondary/40 px-3 py-2.5 text-left transition-colors hover:bg-secondary"
      >
        <Wallet className="h-4 w-4 text-muted-foreground" />
        <div className="min-w-0 flex-1">
          <div className="text-sm font-medium leading-tight">
            {connecting ? "Connecting…" : "Connect wallet"}
          </div>
          <div className="truncate text-xs text-muted-foreground">Solana</div>
        </div>
        {connecting && (
          <span className="h-2 w-2 animate-pulse rounded-full bg-warning" />
        )}
      </button>
    );
  }

  return (
    <div className="rounded-lg border border-border bg-secondary/30 px-3 py-2.5">
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            <button
              onClick={copy}
              className="max-w-full truncate font-mono text-xs text-muted-foreground transition-colors hover:text-foreground"
              title={address ?? undefined}
            >
              {shortAddress(address, 6)}
            </button>
            {copied ? (
              <Check className="h-3 w-3 shrink-0 text-success" />
            ) : (
              <Copy className="h-3 w-3 shrink-0 text-muted-foreground" />
            )}
          </div>
        </div>
        <button
          onClick={disconnect}
          className="shrink-0 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground transition-colors hover:text-destructive"
        >
          Disconnect
        </button>
      </div>
      {isDemo && (
        <div className="mt-1.5 inline-flex items-center gap-1 rounded-full bg-warning/15 px-2 py-0.5 text-[10px] font-semibold text-warning">
          SIMULATED WALLET
        </div>
      )}
    </div>
  );
}

function NetworkIndicator() {
  const { status } = useConfigStatus();
  const mock = status?.payment_mode === "mock";
  const demo = status?.demo_mode === true;

  return (
    <div className="flex flex-col gap-1 px-1 py-2 text-xs">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "h-1.5 w-1.5 rounded-full",
              mock ? "bg-warning animate-pulse-dot" : "bg-success animate-pulse-dot"
            )}
          />
          <span className="text-muted-foreground">
            {mock ? "Demo network" : "Solana Devnet"}
          </span>
        </div>
        <span
          className={cn(
            "rounded border px-1.5 py-0.5 text-[9px] font-bold tracking-wide",
            mock
              ? "border-warning/30 bg-warning/10 text-warning"
              : "border-success/30 bg-success/10 text-success"
          )}
        >
          {mock ? "MOCK MODE" : "USDC LIVE"}
        </span>
      </div>
      {demo && (
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground">Demo build</span>
          <span className="rounded border border-primary/30 bg-primary/10 px-1.5 py-0.5 text-[9px] font-bold tracking-wide text-primary">
            DEMO MODE
          </span>
        </div>
      )}
    </div>
  );
}

function BrandMark({ compact }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-2.5 px-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
        <Landmark className="h-4.5 w-4.5" />
      </div>
      {!compact && (
        <div className="leading-tight">
          <div className="text-[15px] font-bold tracking-tight text-foreground">
            AI Agent Bank
          </div>
          <div className="flex items-center gap-1 text-[10px] text-muted-foreground">
            <ShieldCheck className="h-3 w-3 text-primary" />
            Policy-first money for agents
          </div>
        </div>
      )}
    </div>
  );
}

function SidebarFooter() {
  return (
    <div className="mt-auto flex flex-col gap-1 border-t border-border px-3 py-3">
      <div className="px-1 pb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
        Connected wallet
      </div>
      <WalletStatus />
      <NetworkIndicator />
    </div>
  );
}

export { SidebarNav, SidebarFooter, BrandMark, WalletStatus, NetworkIndicator };