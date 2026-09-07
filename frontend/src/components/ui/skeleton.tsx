import { cn } from "@/lib/utils";

function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-md bg-[linear-gradient(90deg,transparent,hsl(var(--accent)/0.55),transparent)] bg-[length:200%_100%] animate-shimmer",
        "bg-muted/60",
        className
      )}
      {...props}
    />
  );
}

export { Skeleton };