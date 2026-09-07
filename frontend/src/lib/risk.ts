import type { Agent } from "@/lib/types";

export type RiskLevel = "LOW" | "MEDIUM" | "HIGH";

export function riskLevel(agent: Pick<Agent, "status" | "policies" | "total_spent">): {
  level: RiskLevel;
  tone: "success" | "warning" | "destructive";
  reason: string;
} {
  if (agent.status === "killed")
    return { level: "HIGH", tone: "destructive", reason: "Agent terminated" };

  const p = agent.policies;
  if (!p)
    return {
      level: "HIGH",
      tone: "destructive",
      reason: "No policy defined",
    };

  if (!p.blocked_withdrawals || !p.blocked_human_transfers)
    return {
      level: "HIGH",
      tone: "destructive",
      reason: "Withdrawals or human transfers enabled",
    };

  if (p.max_per_day >= 1000)
    return {
      level: "MEDIUM",
      tone: "warning",
      reason: "High daily limit",
    };

  return {
    level: "LOW",
    tone: "success",
    reason: "Limits and permission blocks active",
  };
}

export function spentTodayForAgent(
  transactions: {
    agent_id: number;
    status: string;
    amount: number;
    created_at: string | null;
  }[],
  agentId: number
): number {
  const now = new Date();
  return transactions
    .filter(
      (t) =>
        t.agent_id === agentId &&
        t.status === "executed" &&
        t.created_at &&
        isSameDay(new Date(t.created_at), now)
    )
    .reduce((sum, t) => sum + t.amount, 0);
}

function isSameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}