import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

function ErrorState({
  title = "Something went wrong",
  description,
  onRetry,
}: {
  title?: string;
  description?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-lg border border-destructive/25 bg-destructive/5 px-6 py-12 text-center">
      <div className="flex h-11 w-11 items-center justify-center rounded-full border border-destructive/30 bg-destructive/10 text-destructive">
        <AlertTriangle className="h-5 w-5" />
      </div>
      <div>
        <h3 className="text-sm font-semibold text-foreground">{title}</h3>
        {description && (
          <p className="mx-auto mt-1 max-w-md text-sm text-muted-foreground">{description}</p>
        )}
      </div>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RefreshCw className="h-3.5 w-3.5" />
          Retry
        </Button>
      )}
    </div>
  );
}

export { ErrorState };