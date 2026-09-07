import { cn } from "@/lib/utils";

export interface TabItem {
  value: string;
  label: string;
  icon?: React.ReactNode;
  count?: number;
}

function Tabs<T extends string>({
  tabs,
  value,
  onChange,
  className,
}: {
  tabs: TabItem[];
  value: T;
  onChange: (v: T) => void;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex w-full items-center gap-1 overflow-x-auto border-b border-border",
        className
      )}
      role="tablist"
    >
      {tabs.map((tab) => {
        const active = tab.value === value;
        return (
          <button
            key={tab.value}
            role="tab"
            aria-selected={active}
            type="button"
            onClick={() => onChange(tab.value as T)}
            className={cn(
              "relative -mb-px inline-flex shrink-0 items-center gap-1.5 border-b-2 px-1 py-2.5 text-sm font-medium transition-colors sm:px-3 sm:py-3",
              active
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            )}
          >
            {tab.icon}
            {tab.label}
            {tab.count !== undefined && (
              <span
                className={cn(
                  "ml-0.5 rounded-full px-1.5 py-0.5 text-[10px] font-semibold tabular-nums",
                  active ? "bg-primary/15 text-primary" : "bg-muted text-muted-foreground"
                )}
              >
                {tab.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

export { Tabs };