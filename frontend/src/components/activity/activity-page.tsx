"use client";

import { useBankData } from "@/hooks/use-bank-data";
import { useLiveActivity } from "@/hooks/use-live-activity";
import { PageHeader } from "@/components/layout/page-header";
import { Panel } from "@/components/ui/panel";
import { ErrorState } from "@/components/ui/error-state";
import { ActivityFeed, ActivityFeedSkeleton } from "@/components/activity/activity-feed";
import { Info } from "lucide-react";

export function ActivityPage() {
  const { agents, transactions, loading, error, load, status } = useBankData();
  const { events, playing, toggleLive, clearSimulated, simulatedCount } = useLiveActivity({
    transactions,
    runs: [],
    agents,
    live: true,
  });

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Activity"
        description="A live stream of what agents are doing with money: payment requests, policy decisions, and confirmed transactions."
      />

      {error && <ErrorState description={error} onRetry={() => void load()} />}

      {status?.payment_mode === "mock" && (
        <div className="flex items-start gap-2.5 rounded-lg border border-warning/25 bg-warning/5 px-4 py-3">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
          <p className="text-xs leading-relaxed text-muted-foreground">
            <span className="font-semibold text-warning">MOCK MODE</span> — when no agent is
            transacting, the feed streams <span className="font-medium text-foreground">SIMULATED</span>{" "}
            events so you can see the policy engine in action. Events tagged{" "}
            <span className="font-medium text-foreground">SIM</span> are generated locally and are
            not real blockchain transactions.
          </p>
        </div>
      )}

      <Panel bodyClassName="p-4 sm:p-5" className={loading ? "opacity-90" : undefined}>
        {loading && transactions.length === 0 && agents.length === 0 ? (
          <ActivityFeedSkeleton rows={10} />
        ) : (
          <ActivityFeed
            events={events}
            live={playing}
            toggleLive={toggleLive}
            onClearSimulated={clearSimulated}
          />
        )}
        {simulatedCount > 0 && (
          <p className="mt-4 text-[10px] text-muted-foreground">
            {simulatedCount} simulated event{simulatedCount === 1 ? "" : "s"} in view —
            generated locally for the demo.
          </p>
        )}
      </Panel>
    </div>
  );
}