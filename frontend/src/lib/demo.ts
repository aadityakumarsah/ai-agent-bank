import type { ActivityEvent, ApprovalRequest } from "@/lib/types";

export const SUGGESTED_AGENTS = [
  { name: "ResearchBot", description: "Autonomous research assistant that finds and tests Solana RPC providers." },
  { name: "ComputeBot", description: "Provisions GPU compute and pays infrastructure providers." },
  { name: "DataBot", description: "Buys market data feeds and computes trading signals." },
  { name: "DeployAgent", description: "Provisions compute and deploys services on demand." },
];

export const ACTIVITY_AGENTS = ["ResearchBot", "ComputeBot", "DataBot"];

const CHECK_ALLOWED = [
  { name: "Valid amount", passed: true },
  { name: "Per-transaction limit", passed: true },
  { name: "Daily limit", passed: true },
  { name: "Category allowed", passed: true },
  { name: "Recipient trusted", passed: true },
  { name: "Human approval threshold", passed: true },
];

const CHECK_BLOCKED = [
  { name: "Valid amount", passed: true },
  { name: "Per-transaction limit", passed: true },
  { name: "Daily limit", passed: true },
  { name: "Category allowed", passed: true },
  { name: "Recipient trusted", passed: false },
  { name: "Human transfers enabled", passed: false },
];

const LIVE_POOL: Array<{
  delayMs: number;
  make: (ts: number, seq: number) => ActivityEvent[];
}> = [
  {
    delayMs: 6000,
    make: (ts, seq) => [
      {
        id: `live-${seq}-req`,
        timestamp: ts,
        type: "request",
        agentName: "ResearchBot",
        amount: 0.02,
        currency: "USDC",
        label: "RPC API",
        detail: "Paid RPC provider for query",
        simulated: true,
      },
      {
        id: `live-${seq}-allow`,
        timestamp: ts + 1000,
        type: "policy_allowed",
        agentName: "ResearchBot",
        checks: CHECK_ALLOWED,
        label: "POLICY CHECK",
        detail: "Allowed",
        simulated: true,
      },
      {
        id: `live-${seq}-done`,
        timestamp: ts + 2200,
        type: "payment_completed",
        agentName: "ResearchBot",
        amount: 0.02,
        currency: "USDC",
        label: "Payment completed",
        detail: "MOCK MODE — simulated, nothing on-chain",
        signature: `mock_live_rpc_${seq}`,
        simulated: true,
      },
    ],
  },
  {
    delayMs: 21000,
    make: (ts, seq) => [
      {
        id: `live-${seq}-req`,
        timestamp: ts,
        type: "request",
        agentName: "ComputeBot",
        amount: 300,
        currency: "USDC",
        label: "Unknown wallet",
        detail: "Transfer $300 to beneficiary",
        simulated: true,
      },
      {
        id: `live-${seq}-block`,
        timestamp: ts + 1200,
        type: "policy_blocked",
        agentName: "ComputeBot",
        checks: CHECK_BLOCKED,
        label: "POLICY CHECK",
        detail: "BLOCKED",
        simulated: true,
      },
    ],
  },
];

export function makeLiveActivity(nextId: () => string): ActivityEvent[] {
  const pick = LIVE_POOL[Math.floor(Math.random() * LIVE_POOL.length)];
  const ts = Date.now();
  const seq = Math.floor(Math.random() * 1_000_000);
  return pick.make(ts, seq).map((e, i) => ({ ...e, id: nextId(), timestamp: ts + i * 1000 }));
}

/** Seed approvals flagged as SIMULATED so the Approval Center is demoable offline. */
export function seedApprovals(now: number = Date.now()): ApprovalRequest[] {
  return [
    {
      id: "appr-demo-1",
      agentName: "ResearchBot",
      amount: 25,
      currency: "USDC",
      reason: "Premium data subscription above the $20 threshold.",
      policyNote: "Transactions above $20 require approval.",
      recipientName: "DataMarket Inc.",
      recipient: "dataProvider",
      category: "data",
      expiresAt: now + 14 * 60 * 1000,
      simulated: true,
      status: "pending",
    },
    {
      id: "appr-demo-2",
      agentName: "ComputeBot",
      amount: 150,
      currency: "USDC",
      reason: "GPU compute cluster invoice above the $100 threshold.",
      policyNote: "Transactions above $100 require approval.",
      recipientName: "CloudCompute",
      recipient: "computeProvider",
      category: "compute",
      expiresAt: now + 8 * 60 * 1000,
      simulated: true,
      status: "pending",
    },
    {
      id: "appr-demo-3",
      agentName: "DataBot",
      amount: 75,
      currency: "USDC",
      reason: "Deep-research report above the $50 threshold.",
      policyNote: "Transactions above $50 require approval.",
      recipientName: "AnalyticsFeeds",
      recipient: "apiProvider",
      category: "data",
      expiresAt: now + 4 * 60 * 1000,
      simulated: true,
      status: "pending",
    },
  ];
}