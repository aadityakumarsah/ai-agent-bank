import { cn } from "@/lib/utils";

function StatCard({
  label,
  value,
  hint,
  icon: Icon,
  tone = "default",
  onClick,
  accent,
}: {
  label: string;
  value: React.ReactNode;
  hint?: React.ReactNode;
  icon: React.ElementType;
  tone?: "default" | "success" | "destructive" | "warning" | "info" | "primary";
  onClick?: () => void;
  accent?: boolean;
}) {
  const iconTones: Record<string, string> = {
    default: "text-muted-foreground",
    primary: "text-primary",
    success: "text-success",
    destructive: "text-destructive",
    warning: "text-warning",
    info: "text-info",
  };
  const valueTones: Record<string, string> = {
    default: "text-foreground",
    primary: "text-primary",
    success: "text-success",
    destructive: "text-destructive",
    warning: "text-warning",
    info: "text-info",
  };

  return (
    <div
      onClick={onClick}
      className={cn(
        "group relative overflow-hidden rounded-xl border bg-card p-4",
        onClick && "cursor-pointer transition-colors hover:bg-secondary/40",
        accent && "border-primary/25"
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
            {label}
          </div>
          <div
            className={cn(
              "mt-1.5 text-2xl font-bold tracking-tight tabular-nums",
              valueTones[tone]
            )}
          >
            {value}
          </div>
          {hint && <div className="mt-1 text-xs text-muted-foreground">{hint}</div>}
        </div>
        <div
          className={cn(
            "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-border bg-secondary/50",
            iconTones[tone]
          )}
        >
          <Icon className="h-4 w-4" />
        </div>
      </div>
    </div>
  );
}

export { StatCard };