import { cn } from "@/lib/utils";

function ProgressRing({
  value,
  size = 160,
  stroke = 12,
  tone = "primary",
  trackClassName,
  children,
}: {
  value: number;
  size?: number;
  stroke?: number;
  tone?: "primary" | "success" | "warning" | "destructive" | "info";
  trackClassName?: string;
  children?: React.ReactNode;
}) {
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.min(100, Math.max(0, value));
  const offset = circumference * (1 - clamped / 100);

  const tones: Record<string, string> = {
    primary: "#2dd4a0",
    success: "#34d399",
    warning: "#f59e0b",
    destructive: "#ef4444",
    info: "#60a5fa",
  };

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={stroke}
          className={trackClassName ?? "stroke-muted"}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={tones[tone]}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 0.7s cubic-bezier(0.4,0,0.2,1)" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">{children}</div>
    </div>
  );
}

export { ProgressRing };

export function ToneDot({ tone = "primary", className }: { tone?: string; className?: string }) {
  const tones: Record<string, string> = {
    primary: "bg-primary",
    success: "bg-success",
    warning: "bg-warning",
    destructive: "bg-destructive",
    info: "bg-info",
    neutral: "bg-muted-foreground",
  };
  return <span className={cn("inline-block h-1.5 w-1.5 rounded-full", tones[tone], className)} />;
}

export function StatusDot({ tone = "success", className }: { tone?: string; className?: string }) {
  const tones: Record<string, string> = {
    success: "bg-success",
    warning: "bg-warning",
    destructive: "bg-destructive",
    info: "bg-info",
    neutral: "bg-muted-foreground",
  };
  return (
    <span className={cn("relative inline-flex h-2 w-2", className)}>
      <span
        className={cn("absolute inline-flex h-full w-full rounded-full opacity-40 animate-ping", tones[tone])}
      />
      <span className={cn("relative inline-flex h-2 w-2 rounded-full", tones[tone])} />
    </span>
  );
}