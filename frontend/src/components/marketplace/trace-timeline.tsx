"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Check,
  CircleDashed,
  CircleCheck,
  ShieldOff,
  XCircle,
  Play,
  RotateCcw,
} from "lucide-react";
import type { TraceStep, TraceState } from "@/lib/types";
import { cn } from "@/lib/utils";

const STEP_STYLES: Record<
  TraceState,
  { node: string; label: string; connector: string; ring: string }
> = {
  done: {
    node: "border-primary bg-primary text-primary-foreground",
    label: "text-foreground",
    connector: "bg-primary",
    ring: "",
  },
  success: {
    node: "border-success bg-success text-success-foreground",
    label: "text-foreground",
    connector: "bg-success",
    ring: "shadow-[0_0_18px_rgba(52,199,123,0.35)]",
  },
  active: {
    node: "border-warning bg-warning/10 text-warning",
    label: "text-foreground",
    connector: "bg-warning",
    ring: "shadow-[0_0_18px_rgba(250,204,21,0.25)]",
  },
  error: {
    node: "border-destructive bg-destructive text-destructive-foreground",
    label: "text-destructive",
    connector: "bg-destructive",
    ring: "shadow-[0_0_18px_rgba(239,68,68,0.35)]",
  },
  upcoming: {
    node: "border-border bg-card text-muted-foreground",
    label: "text-muted-foreground",
    connector: "bg-border",
    ring: "",
  },
};

function StepIcon({ state }: { state: TraceState }) {
  if (state === "done") return <Check className="h-3.5 w-3.5" />;
  if (state === "success") return <CircleCheck className="h-3.5 w-3.5" />;
  if (state === "error") return <XCircle className="h-3.5 w-3.5" />;
  if (state === "active") return <CircleDashed className="h-3.5 w-3.5 animate-spin" />;
  return null;
}

export function TraceTimeline({ steps }: { steps: TraceStep[] }) {
  return (
    <ol className="relative flex flex-col gap-0">
      {steps.map((step, i) => {
        const style = STEP_STYLES[step.state] ?? STEP_STYLES.upcoming;
        const isLast = i === steps.length - 1;
        return (
          <li key={step.key} className="flex gap-3">
            {/* Node + connector */}
            <div className="flex w-8 shrink-0 flex-col items-center">
              <div
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-full border-2 transition-all",
                  style.node,
                  style.ring
                )}
              >
                <StepIcon state={step.state} />
              </div>
              {!isLast && (
                <div
                  className={cn(
                    "my-1 w-0.5 flex-1 transition-colors",
                    style.connector
                  )}
                  style={{ minHeight: 24 }}
                />
              )}
            </div>
            {/* Step content */}
            <div className="pb-6 pt-1">
              <div
                className={cn(
                  "flex items-center gap-2 text-sm font-semibold tracking-tight",
                  style.label
                )}
              >
                {step.label}
                {step.state === "error" && (
                  <ShieldOff className="h-3.5 w-3.5 text-destructive" />
                )}
              </div>
              <div className="mt-0.5 font-mono text-xs text-muted-foreground">
                {step.detail}
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}

/**
 * Plays a completed server-side trace as a cinematic reveal.
 * Each step transitions from upcoming -> active (pulse) -> its final state.
 */
function TracePlayer({
  steps,
  autoPlay = false,
  onStart,
  onDone,
}: {
  steps: TraceStep[];
  autoPlay?: boolean;
  onStart?: () => void;
  onDone?: () => void;
}) {
  const revealed = useMemo(
    () => steps.map((s) => ({ ...s, state: "upcoming" as const })),
    [steps]
  );

  const [visible, setVisible] = useState(0);
  const [playing, setPlaying] = useState(autoPlay);

  // Build the display list: steps 0..visible-1 fully revealed, step visible as active.
  const display = useMemo<TraceStep[]>(() => {
    return revealed.map((step, i) => {
      if (i < visible) {
        const finalState: TraceState =
          steps[i]?.state === "error" ? "error" : "done";
        return { ...step, state: finalState };
      }
      if (i === visible && playing) {
        return { ...step, state: "active" as TraceState };
      }
      return step;
    });
  }, [revealed, visible, playing, steps]);

  const play = useCallback(() => {
    setVisible(0);
    setPlaying(true);
    onStart?.();
  }, [onStart]);

  useEffect(() => {
    if (!playing) return;
    if (visible >= steps.length) {
      setPlaying(false);
      onDone?.();
      return;
    }
    const delay = visible === 0 ? 500 : steps[visible]?.state === "error" ? 700 : 650;
    const t = setTimeout(() => setVisible((v) => v + 1), delay);
    return () => clearTimeout(t);
  }, [playing, visible, steps, onDone]);

  return (
    <div>
      {!playing && visible === 0 && (
        <button
          onClick={play}
          className="inline-flex h-9 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          <Play className="h-4 w-4" />
          Play trace
        </button>
      )}
      <div className={cn("mt-4", visible === 0 && "opacity-40")}>
        <TraceTimeline steps={display} />
      </div>
      {visible === steps.length && playing === false && (
        <button
          onClick={play}
          className="inline-flex h-8 items-center gap-2 rounded-md border border-border px-3 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          Replay
        </button>
      )}
    </div>
  );
}

export { TracePlayer };