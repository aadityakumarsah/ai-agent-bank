"use client";

import { Tag, TriangleAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { categoryIcon, categoryLabel, RISK_TONES } from "@/lib/marketplace";
import { formatUsdc } from "@/lib/utils";
import { cn } from "@/lib/utils";
import type { MarketService } from "@/lib/types";

export function ServiceCard({
  service,
  onUse,
  selected,
  disabled,
  compact = false,
}: {
  service: MarketService;
  onUse?: () => void;
  selected?: boolean;
  disabled?: boolean;
  compact?: boolean;
}) {
  const Icon = categoryIcon(service.category);

  return (
    <div
      className={cn(
        "relative flex flex-col gap-3 rounded-xl border bg-card p-4 transition-colors",
        selected
          ? "border-primary/50 ring-1 ring-primary/30"
          : "border-border",
        !compact && "hover:border-primary/30"
      )}
    >
      {service.is_demo && (
        <span className="absolute right-3 top-3 rounded bg-warning/15 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-widest text-warning">
          Demo service
        </span>
      )}

      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-border bg-secondary text-primary">
          <Icon className="h-4.5 w-4.5" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-semibold text-foreground">
            {service.name}
          </div>
          <div className="mt-0.5 flex items-center gap-1.5 text-xs text-muted-foreground">
            <Badge variant="outline" className="px-1.5 py-0 text-[10px]">
              {categoryLabel(service.category)}
            </Badge>
            <span className="font-mono text-[11px]">{service.endpoint}</span>
          </div>
        </div>
      </div>

      {service.description && (
        <p className="text-xs leading-relaxed text-muted-foreground">
          {service.description}
        </p>
      )}

      <div className="mt-auto flex items-center justify-between gap-2 border-t border-border pt-3">
        <div className="flex items-center gap-2">
          <Tag className="h-3.5 w-3.5 text-primary" />
          <span className="text-sm font-bold tabular-nums text-foreground">
            {formatUsdc(service.price)}
          </span>
          <span className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            {service.currency}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <Badge variant={RISK_TONES[service.risk_level] ?? "neutral"} className="gap-1 px-1.5 py-0 text-[10px]">
            <TriangleAlert className="h-2.5 w-2.5" />
            {service.risk_level}
          </Badge>
          {onUse && (
            <button
              onClick={onUse}
              disabled={disabled}
              className={cn(
                "inline-flex h-7 items-center rounded-md px-2.5 text-xs font-medium transition-colors",
                disabled
                  ? "cursor-not-allowed bg-secondary text-muted-foreground/50"
                  : "bg-primary text-primary-foreground hover:bg-primary/90"
              )}
            >
              Use service
            </button>
          )}
        </div>
      </div>
    </div>
  );
}