"use client";

import { useState } from "react";
import { Menu, X } from "lucide-react";
import { BrandMark, SidebarFooter, SidebarNav } from "./sidebar";
import { WalletConnectButton } from "@/components/wallet/wallet-connect-button";

function MobileDrawer() {
  const [open, setOpen] = useState(false);

  return (
    <div className="lg:hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="rounded-md p-2 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
        aria-label="Toggle navigation"
      >
        {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </button>
      {open && (
        <div className="fixed inset-x-0 top-16 z-40 border-b border-border bg-background shadow-lg shadow-black/40 animate-fade-in">
          <div className="flex flex-col gap-2 p-4 pb-6">
            <SidebarNav onNavigate={() => setOpen(false)} />
            <SidebarFooter />
          </div>
        </div>
      )}
    </div>
  );
}

function MobileHeader() {
  return (
    <div className="sticky top-0 z-50 flex h-16 items-center justify-between border-b border-border bg-background/85 px-4 backdrop-blur lg:hidden">
      <div className="flex items-center gap-2">
        <MobileDrawer />
        <BrandMark compact />
      </div>
      <WalletConnectButton compact />
    </div>
  );
}

export function AppShell({
  children,
  footer = true,
}: {
  children: React.ReactNode;
  footer?: boolean;
}) {
  return (
    <div className="flex min-h-screen w-full bg-background">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-60 flex-col border-r border-border bg-sidebar lg:flex">
        <div className="flex h-16 items-center border-b border-border px-2">
          <BrandMark />
        </div>
        <div className="flex h-full flex-col py-4">
          <SidebarNav />
          <SidebarFooter />
        </div>
      </aside>

      {/* Main column */}
      <div className="flex min-w-0 flex-1 flex-col lg:pl-60">
        <MobileHeader />
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6 lg:px-10 lg:py-8">
          {children}
        </main>
        {footer && (
          <footer className="border-t border-border py-6">
            <div className="mx-auto max-w-6xl px-6 lg:px-10">
              <p className="text-center text-xs text-muted-foreground">
                AI Agent Bank — the AI proposes, the policy engine decides, the
                blockchain executes. Humans stay in control.
              </p>
            </div>
          </footer>
        )}
      </div>
    </div>
  );
}