import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

function Spinner({
  className,
  label = "Loading…",
}: {
  className?: string;
  label?: string;
}) {
  return (
    <div className="flex items-center justify-center gap-2.5 py-10 text-sm text-muted-foreground">
      <Loader2 className={cn("h-4.5 w-4.5 animate-spin text-primary", className)} />
      {label}
    </div>
  );
}

export { Spinner };