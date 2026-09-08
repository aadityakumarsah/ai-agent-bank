"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ActivityEvent, Agent, Transaction } from "@/lib/types";
import { useConfigStatus } from "@/hooks/use-config-status";
import {
  buildActivity,
  mergeActivity,
  pushSimulated,
  runsToActivity,
  summarizeAgents,
} from "@/lib/activity";

export function useLiveActivity({
  transactions,
  runs,
  agents,
  live = true,
  intervalMs = 14000,
}: {
  transactions: Transaction[];
  runs: { run_id: number; status: string; created_at?: string | null }[];
  agents: Agent[];
  live?: boolean;
  intervalMs?: number;
}) {
  const { status } = useConfigStatus();
  const demoMode = status?.demo_mode === true;

  const [simulated, setSimulated] = useState<ActivityEvent[]>([]);
  // Live simulated streaming only ever happens in DEMO_MODE. In real mode the
  // feed is 100% real on-chain activity — there is no fake stream to toggle on.
  const [playing, setPlaying] = useState(false);
  const playingRef = useRef(playing);
  playingRef.current = playing;

  const boundedSimulated = useMemo(() => simulated.slice(0, 120), [simulated]);

  const liveAllowed = demoMode && live;

  useEffect(() => {
    if (liveAllowed) setPlaying(true);
  }, [liveAllowed]);

  useEffect(() => {
    if (!playing || !demoMode) return;
    const id = window.setInterval(() => {
      setSimulated((prev) => pushSimulated(prev));
    }, intervalMs);
    return () => window.clearInterval(id);
  }, [playing, demoMode, intervalMs]);

  const baseEvents = useMemo(() => {
    const idToName = summarizeAgents(agents);
    const runEvents = runsToActivity(runs);
    return buildActivity(transactions, runEvents, idToName);
  }, [transactions, runs, agents]);

  const events = useMemo(
    () => mergeActivity([...boundedSimulated, ...baseEvents]),
    [boundedSimulated, baseEvents]
  );

  const clearSimulated = useCallback(() => setSimulated([]), []);
  const toggleLive = useCallback(() => {
    if (!demoMode) return;
    setPlaying((v) => !v);
  }, [demoMode]);

  return { events, simulatedCount: simulated.length, playing, toggleLive, clearSimulated };
}