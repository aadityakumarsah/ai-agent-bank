"use client";

import { WalletProvider } from "@/components/wallet/wallet-context";
import { ToastProvider } from "@/components/ui/toast";
import { ApprovalsProvider } from "@/components/approvals/approvals-context";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ToastProvider>
      <ApprovalsProvider>
        <WalletProvider>{children}</WalletProvider>
      </ApprovalsProvider>
    </ToastProvider>
  );
}