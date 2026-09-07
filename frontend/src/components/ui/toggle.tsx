import { cn } from "@/lib/utils";

export function Toggle({
  checked,
  onCheckedChange,
  label,
  description,
  disabled,
  className,
  sizing = "md",
}: {
  checked: boolean;
  onCheckedChange: (v: boolean) => void;
  label?: string;
  description?: string;
  disabled?: boolean;
  className?: string;
  sizing?: "md" | "sm";
}) {
  const size = sizing === "sm" ? "h-5 w-9" : "h-6 w-11";
  const knob = sizing === "sm" ? "h-4 w-4" : "h-5 w-5";
  const knobTranslate = sizing === "sm" ? "translate-x-4" : "translate-x-5";

  const control = (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onCheckedChange(!checked)}
      className={cn(
        "relative inline-flex shrink-0 cursor-pointer items-center rounded-full border transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-40",
        size,
        checked ? "border-transparent bg-primary" : "border-border bg-secondary",
        className
      )}
    >
      <span
        className={cn(
          "pointer-events-none inline-block rounded-full bg-background shadow-sm transition-transform duration-200",
          knob,
          checked && knobTranslate
        )}
      />
    </button>
  );

  if (!label) return control;

  return (
    <div className="flex items-center justify-between gap-4">
      <div className="min-w-0">
        <div className="text-sm font-medium leading-tight text-foreground">{label}</div>
        {description && (
          <div className="mt-0.5 text-xs leading-snug text-muted-foreground">{description}</div>
        )}
      </div>
      {control}
    </div>
  );
}

export { Toggle as Switch };