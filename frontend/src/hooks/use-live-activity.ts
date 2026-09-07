"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ActivityEvent, Agent, Transaction } from "@/lib/types";
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
  const [simulated, setSimulated] = useState<ActivityEvent[]>([]);
  const [playing, setPlaying] = useState(live);
  const playingRef = useRef(playing);
  playingRef.current = playing;

  const boundedSimulated = useMemo(() => simulated.slice(0, 120), [simulated]);

  useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(() => {
      setSimulated((prev) => pushSimulated(prev));
    }, intervalMs);
    return () => window.clearInterval(id);
  }, [playing, intervalMs]);

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
  const toggleLive = useCallback(() => setPlaying((v) => !v), []);

  return { events, simulatedCount: simulated.length, playing, toggleLive, clearSimulated };
}