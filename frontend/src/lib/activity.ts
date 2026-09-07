import type { ActivityEvent, Agent, Transaction } from "@/lib/types";
import { makeLiveActivity } from "@/lib/demo";

let counter = 0;

export function nextActivityId(): string {
  counter += 1;
  return `evt-${Date.now().toString(36)}-${counter}-${Math.floor(Math.random() * 1e6).toString(36)}`;
}

export function transactionToActivity(
  tx: Transaction,
  agentName?: string
): ActivityEvent | null {
  const base = {
    id: `tx-${tx.id}`,
    timestamp: tx.created_at ? new Date(tx.created_at).getTime() : Date.now(),
    agentName: agentName ?? `Agent #${tx.agent_id}`,
    amount: tx.amount,
    currency: tx.currency,
  };

  switch (tx.status) {
    case "executed":
      return {
        ...base,
        type: "payment_completed",
        label: "Payment completed",
        detail: "Solana transaction confirmed",
        signature: tx.tx_hash,
      };
    case "rejected":
      return {
        ...base,
        type: "policy_blocked",
        label: "POLICY CHECK",
        detail: "BLOCKED",
        checks: [
          { name: "Valid amount", passed: true },
          { name: "Policy engine", passed: false },
          { name: "Recipient trusted", passed: false },
        ],
      };
    case "pending":
    case "approved":
      return {
        ...base,
        type: "approval_required",
        label: "Approval required",
        detail: "Awaiting human decision",
      };
    case "failed":
      return {
        ...base,
        type: "payment_failed",
        label: "Payment failed",
        detail: tx.rejection_reason ?? "Execution failed",
      };
    default:
      return null;
  }
}

export function runsToActivity(
  runs: { run_id: number; status: string; created_at?: string | null }[],
  agentName?: string
): ActivityEvent[] {
  return runs
    .filter((r) => Boolean(r.created_at))
    .map((r) => ({
      id: `run-${r.run_id}`,
      timestamp: new Date(r.created_at!).getTime(),
      type: "task_started" as const,
      agentName: agentName ?? "Agent",
      label: r.status === "completed" ? "Task completed" : r.status,
      detail: "Agent runtime",
    }));
}

export function buildActivity(
  transactions: Transaction[],
  runs: ActivityEvent[],
  agentIdToName: Map<number, string>
): ActivityEvent[] {
  const fromTxs = transactions
    .map((t) => transactionToActivity(t, agentIdToName.get(t.agent_id)))
    .filter((e): e is ActivityEvent => e !== null);
  return [...fromTxs, ...runs];
}

export function mergeActivity(list: ActivityEvent[]): ActivityEvent[] {
  return [...list].sort((a, b) => b.timestamp - a.timestamp).slice(0, 200);
}

export function pushSimulated(prev: ActivityEvent[]): ActivityEvent[] {
  const fresh = makeLiveActivity(nextActivityId).map((e) => ({ ...e, simulated: true }));
  return mergeActivity([...fresh, ...prev]);
}

export function summarizeAgents(agents: Agent[]): Map<number, string> {
  return new Map(agents.map((a) => [a.id, a.name]));
}