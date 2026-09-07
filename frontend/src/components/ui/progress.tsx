import { cn } from "@/lib/utils";

function Progress({
  value,
  className,
  indicatorClassName,
  tone = "primary",
}: {
  value: number;
  className?: string;
  indicatorClassName?: string;
  tone?: "primary" | "success" | "warning" | "destructive" | "info";
}) {
  const tones: Record<string, string> = {
    primary: "bg-primary",
    success: "bg-success",
    warning: "bg-warning",
    destructive: "bg-destructive",
    info: "bg-info",
  };

  return (
    <div
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={value}
      className={cn("h-1.5 w-full overflow-hidden rounded-full bg-muted", className)}
    >
      <div
        className={cn(
          "h-full rounded-full transition-[width] duration-500 ease-out",
          tones[tone],
          indicatorClassName
        )}
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  );
}

function Indeterminate({ className }: { className?: string }) {
  return (
    <div className={cn("relative h-0.5 w-full overflow-hidden rounded-full bg-muted", className)}>
      <div className="h-full w-1/3 animate-indeterminate rounded-full bg-primary" />
    </div>
  );
}

export { Progress, Indeterminate };