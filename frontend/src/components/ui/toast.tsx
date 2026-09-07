"use client";

import * as React from "react";
import { createContext, useCallback, useContext, useRef, useState } from "react";
import { CheckCircle2, XCircle, Info, AlertTriangle, X } from "lucide-react";
import { cn } from "@/lib/utils";

type ToastType = "success" | "error" | "info" | "warning";

interface Toast {
  id: number;
  type: ToastType;
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void };
}

interface ToastContextValue {
  toast: (t: Omit<Toast, "id">) => void;
  dismiss: (id: number) => void;
}

const ToastContext = createContext<ToastContextValue>({
  toast: () => {},
  dismiss: () => {},
});

export function useToast() {
  return useContext(ToastContext);
}

const toastStyles: Record<ToastType, { icon: React.ReactNode; ring: string }> = {
  success: {
    icon: <CheckCircle2 className="h-4.5 w-4.5 text-success" />,
    ring: "border-success/25",
  },
  error: {
    icon: <XCircle className="h-4.5 w-4.5 text-destructive" />,
    ring: "border-destructive/25",
  },
  info: {
    icon: <Info className="h-4.5 w-4.5 text-info" />,
    ring: "border-info/25",
  },
  warning: {
    icon: <AlertTriangle className="h-4.5 w-4.5 text-warning" />,
    ring: "border-warning/25",
  },
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const idRef = useRef(0);

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback(
    (t: Omit<Toast, "id">) => {
      const id = ++idRef.current;
      setToasts((prev) => [...prev, { ...t, id }]);
      if (t.type !== "error") {
        window.setTimeout(() => dismiss(id), t.type === "warning" ? 5000 : 3800);
      }
    },
    [dismiss]
  );

  return (
    <ToastContext.Provider value={{ toast, dismiss }}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-[100] flex w-[min(24rem,calc(100vw-2rem))] flex-col gap-2">
        {toasts.map((t) => {
          const style = toastStyles[t.type];
          return (
            <div
              key={t.id}
              role="status"
              className={cn(
                "pointer-events-auto flex items-start gap-3 rounded-lg border bg-card/95 px-3.5 py-3 shadow-lg shadow-black/40 backdrop-blur animate-slide-in-right",
                style.ring
              )}
            >
              <div className="mt-0.5 shrink-0">{style.icon}</div>
              <div className="min-w-0 flex-1">
                <div className="text-sm font-semibold leading-tight text-foreground">
                  {t.title}
                </div>
                {t.description && (
                  <div className="mt-0.5 text-xs leading-snug text-muted-foreground">
                    {t.description}
                  </div>
                )}
                {t.action && (
                  <button
                    onClick={() => {
                      t.action?.onClick();
                      dismiss(t.id);
                    }}
                    className="mt-1.5 text-xs font-semibold text-primary hover:text-primary/80"
                  >
                    {t.action.label}
                  </button>
                )}
              </div>
              <button
                onClick={() => dismiss(t.id)}
                className="shrink-0 rounded p-0.5 text-muted-foreground transition-colors hover:text-foreground"
                aria-label="Dismiss"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}