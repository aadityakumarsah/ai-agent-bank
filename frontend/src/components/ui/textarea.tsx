import * as React from "react";
import { cn } from "@/lib/utils";

const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement> & { label?: string }
>(({ className, label, id, ...props }, ref) => (
  <div className="flex flex-col gap-1.5">
    {label ? (
      <label htmlFor={id} className="text-sm font-medium text-muted-foreground">
        {label}
      </label>
    ) : null}
    <textarea
      ref={ref}
      id={id}
      className={cn(
        "flex min-h-[80px] w-full rounded-md border border-input bg-card px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}
    />
  </div>
));
Textarea.displayName = "Textarea";

export { Textarea };