import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

function Stepper({
  steps,
  current,
  className,
}: {
  steps: string[];
  current: number;
  className?: string;
}) {
  return (
    <ol className={cn("flex items-center gap-0", className)} aria-label="Progress">
      {steps.map((label, i) => {
        const state = i < current ? "done" : i === current ? "active" : "upcoming";
        return (
          <li key={label} className="flex flex-1 items-center last:flex-none">
            <div className="flex flex-col items-center gap-1.5 sm:flex-row sm:gap-2.5">
              <div
                className={cn(
                  "flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-[11px] font-semibold transition-colors",
                  state === "done" && "border-primary bg-primary text-primary-foreground",
                  state === "active" && "border-primary bg-primary/10 text-primary",
                  state === "upcoming" && "border-border bg-card text-muted-foreground"
                )}
                aria-current={state === "active" ? "step" : undefined}
              >
                {state === "done" ? <Check className="h-3.5 w-3.5" /> : i + 1}
              </div>
              <span
                className={cn(
                  "hidden text-xs font-medium sm:block",
                  state === "active" ? "text-foreground" : "text-muted-foreground"
                )}
              >
                {label}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div
                className={cn(
                  "mx-2 h-px flex-1 sm:mx-3",
                  i < current ? "bg-primary" : "bg-border"
                )}
              />
            )}
          </li>
        );
      })}
    </ol>
  );
}

export { Stepper };