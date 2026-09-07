"use client";

import { useMemo, useState } from "react";
import { Store, TriangleAlert } from "lucide-react";
import { Panel } from "@/components/ui/panel";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { ServiceCard } from "@/components/marketplace/service-card";
import { CATEGORY_META, CATEGORY_ORDER, categoryIcon } from "@/lib/marketplace";
import { cn } from "@/lib/utils";
import type { MarketService, ServiceCategory } from "@/lib/types";

export function DirectorySection({
  services,
  loading,
  error,
  onRetry,
  selectedId,
  onSelect,
}: {
  services: MarketService[];
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  selectedId?: number | null;
  onSelect?: (id: number) => void;
}) {
  const [category, setCategory] = useState<ServiceCategory | "all">("all");

  const filtered = useMemo(
    () => (category === "all" ? services : services.filter((s) => s.category === category)),
    [services, category]
  );

  const demoCount = services.filter((s) => s.is_demo).length;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            onClick={() => setCategory("all")}
            className={cn(
              "rounded-full border px-3 py-1.5 text-xs font-medium transition-colors",
              category === "all"
                ? "border-primary/40 bg-primary/10 text-primary"
                : "border-border bg-card text-muted-foreground hover:text-foreground"
            )}
          >
            All
            <span className="ml-1.5 tabular-nums text-muted-foreground">{services.length}</span>
          </button>
          {CATEGORY_ORDER.map((c) => {
            const Icon = CATEGORY_META[c].icon;
            const count = services.filter((s) => s.category === c).length;
            return (
              <button
                key={c}
                onClick={() => setCategory(c)}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors",
                  category === c
                    ? "border-primary/40 bg-primary/10 text-primary"
                    : "border-border bg-card text-muted-foreground hover:text-foreground"
                )}
              >
                <Icon className="h-3 w-3" />
                {CATEGORY_META[c].label}
                <span className="tabular-nums text-muted-foreground">{count}</span>
              </button>
            );
          })}
        </div>
        <Badge variant="warning" className="gap-1.5 self-start sm:self-auto">
          <TriangleAlert className="h-3 w-3" />
          {demoCount} demo listings
        </Badge>
      </div>

      {error && <ErrorState description={error} onRetry={onRetry} />}

      {loading && services.length === 0 ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-40" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <Panel>
          <EmptyState
            icon={Store}
            title={category === "all" ? "No services listed" : "No services in this category"}
            description="The service directory is empty. Demo services are added automatically on startup."
          />
        </Panel>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((s) => (
            <ServiceCard
              key={s.id}
              service={s}
              selected={selectedId === s.id}
              onUse={selectedId === s.id ? undefined : () => onSelect?.(s.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function CategoryIcon({ category }: { category: ServiceCategory }) {
  const Icon = categoryIcon(category);
  return <Icon className="h-4 w-4" />;
}