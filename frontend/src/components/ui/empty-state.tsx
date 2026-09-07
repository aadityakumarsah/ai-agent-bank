import type { LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";

export function EmptyState({
  icon: Icon,
  title,
  description,
  actionLabel,
  onAction,
  className,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}) {
  return (
    <div
      className={`flex flex-col items-center gap-3 rounded-lg border border-dashed border-border bg-card/40 px-6 py-14 text-center ${className ?? ""}`}
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-full border border-border bg-secondary text-muted-foreground">
        <Icon className="h-5 w-5" />
      </div>
      <div>
        <h3 className="text-sm font-semibold text-foreground">{title}</h3>
        <p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">{description}</p>
      </div>
      {actionLabel && onAction && (
        <Button variant="secondary" size="sm" onClick={onAction} className="mt-1">
          {actionLabel}
        </Button>
      )}
    </div>
  );
}