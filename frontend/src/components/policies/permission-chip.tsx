import type { PermissionDef } from "@/lib/types";
import { cn } from "@/lib/utils";

function PermissionChip({
  permission,
  enabled,
}: {
  permission: PermissionDef;
  enabled: boolean;
}) {
  return (
    <div
      className={cn(
        "flex items-center justify-between gap-3 rounded-lg border px-3 py-2",
        enabled ? "border-success/25 bg-success/[0.04]" : "border-border bg-card/50 opacity-70"
      )}
    >
      <div className="min-w-0">
        <div className="text-sm font-medium text-foreground">{permission.label}</div>
        <div className="truncate text-xs text-muted-foreground">{permission.description}</div>
      </div>
      <span
        className={cn(
          "shrink-0 rounded px-1.5 py-0.5 text-[10px] font-bold tracking-wide",
          enabled ? "bg-success/15 text-success" : "bg-muted text-muted-foreground"
        )}
      >
        {enabled ? "ON" : "OFF"}
      </span>
    </div>
  );
}

function PermissionRow({ label, enabled }: { label: string; enabled: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3 py-2">
      <div className="text-sm text-foreground">{label}</div>
      <span
        className={cn(
          "rounded px-1.5 py-0.5 text-[10px] font-bold tracking-wide",
          enabled ? "bg-success/15 text-success" : "bg-muted text-muted-foreground"
        )}
      >
        {enabled ? "ON" : "OFF"}
      </span>
    </div>
  );
}

export { PermissionChip, PermissionRow };