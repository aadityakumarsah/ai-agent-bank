import * as React from "react";
import { cn } from "@/lib/utils";

export type InputProps = React.InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  prefix?: string;
  hint?: string;
};

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, label, id, prefix, hint, ...props }, ref) => (
    <div className="flex flex-col gap-1.5">
      {label ? (
        <label htmlFor={id} className="text-sm font-medium text-muted-foreground">
          {label}
        </label>
      ) : null}
      <div className="relative">
        {prefix ? (
          <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-sm text-muted-foreground">
            {prefix}
          </span>
        ) : null}
        <input
          type={type}
          ref={ref}
          id={id}
          className={cn(
            "flex h-10 w-full rounded-md border border-input bg-card px-3 py-2 text-sm text-foreground ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-0 disabled:cursor-not-allowed disabled:opacity-50",
            prefix && "pl-7",
            className
          )}
          {...props}
        />
      </div>
      {hint ? <p className="text-xs text-muted-foreground">{hint}</p> : null}
    </div>
  )
);
Input.displayName = "Input";

export { Input };