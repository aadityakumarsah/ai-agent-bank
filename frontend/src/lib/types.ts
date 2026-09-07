export type AgentStatus = "active" | "suspended" | "killed";

export type ServiceCategory =
  | "api"
  | "compute"
  | "data"
  | "ai_model"
  | "storage"
  | "other_agent";

export interface MarketService {
  id: number;
  name: string;
  description: string | null;
  category: ServiceCategory;
  endpoint: string;
  wallet_address: string;
  price: number;
  currency: string;
  requires_payment: boolean;
  active: boolean;
  risk_level: "low" | "medium" | "high";
  is_demo: boolean;
}

export type TraceState = "done" | "active" | "success" | "error" | "upcoming";

export interface TraceStep {
  key: string;
  label: string;
  detail: string;
  t?: string;
  state: TraceState;
}

export type DemoFlow =
  | "completed"
  | "blocked"
  | "approval_required"
  | "failed";

export interface DemoResult {
  flow: DemoFlow;
  approved: boolean;
  trace: TraceStep[];
  checks: PolicyCheck[];
  reason?: string;
  suggestion?: string;
  transaction: Transaction | null;
  proof?: {
    tx_hash: string;
    mode: string;
    simulated: boolean;
    explorer_url?: string | null;
  };
  summary?: string;
  agent_name?: string;
  service?: MarketService;
  demo_task?: string;
}

export interface ServiceRequestResult {
  status: "ok" | "payment_required";
  http_status_hint?: number;
  x402_note?: string;
  service_id: number;
  service_name: string;
  payment_required: boolean;
  demo: boolean;
  payment_info?: {
    amount: number;
    currency: string;
    recipient_address: string;
    recipient_name: string;
    category: string;
    endpoint: string;
  };
  result?: Record<string, unknown>;
}

export interface ServicePaymentResult {
  status: "paid" | "blocked" | "approval_required" | "failed";
  approved: boolean;
  payment_required: boolean;
  blocked?: boolean;
  reason?: string;
  checks: PolicyCheck[];
  transaction: Transaction | null;
  suggestion?: string;
  proof?: {
    tx_hash: string;
    mode: string;
    simulated: boolean;
    explorer_url?: string | null;
  };
  service?: MarketService;
  retry_with_proof?: boolean;
}

export interface Policy {
  id: number;
  agent_id: number;
  max_per_transaction: number;
  max_per_day: number;
  max_per_month: number | null;
  allowed_categories: string[];
  blocked_human_transfers: boolean;
  blocked_withdrawals: boolean;
  blocked_arbitrary_contracts: boolean;
  require_approval_above: number | null;
  allowed_recipient_addresses: string[];
}

export interface Agent {
  id: number;
  name: string;
  description: string | null;
  balance: number;
  total_spent: number;
  status: AgentStatus;
  escrow_address: string | null;
  policies: Policy | null;
  created_at: string | null;
}

export interface Transaction {
  id: number;
  agent_id: number;
  amount: number;
  currency: string;
  transaction_type: string;
  status: "pending" | "approved" | "rejected" | "executed" | "failed";
  recipient_address: string;
  recipient_name: string | null;
  category: string | null;
  description: string | null;
  tx_hash: string | null;
  rejection_reason: string | null;
  created_at: string | null;
}

export interface PolicyCheck {
  name: string;
  passed: boolean;
  requested?: string;
  allowed?: string;
  detail?: string;
}

export interface PolicyDecision {
  allowed: boolean;
  reason: string;
  requires_approval: boolean;
  checks: PolicyCheck[];
}

export interface TaskRunResult {
  run_id: number;
  status: string;
  result?: string;
  blocked?: boolean;
  approval_required?: boolean;
  decision?: PolicyDecision;
  transaction?: Transaction | null;
  error?: string | null;
  steps?: Array<Record<string, unknown>>;
}

export interface ConfigStatus {
  payment_mode: "mock" | "real";
  payment_configured: boolean;
  solana_configured: boolean;
  solana_network: "devnet" | "mainnet-beta";
  solana_usdc_mint?: string | null;
  rpc_configured: boolean;
  redis_configured: boolean;
  llm_provider: string;
  llm_configured: boolean;
  use_real_payment: boolean;
  demo_mode: boolean;
  demo_scenarios?: unknown;
  missing_config: string[];
}

export interface LLMKeyStatus {
  provider: "openai" | "anthropic" | "google";
  has_key: boolean;
  source: "user" | "server" | "mock";
}

export interface LLMKeyMessage {
  provider: string;
  message: string;
}

export type ScenarioId = "success" | "blocked-spend" | "blocked-transfer" | "approval";

export interface DemoScenario {
  id: ScenarioId;
  title: string;
  badge: string;
  task: string;
  amount: number;
  outcome: "completed" | "blocked" | "approval_required" | "failed";
}

export interface DemoScenarioRunResult extends DemoResult {
  scenario: ScenarioId;
  scenario_title: string;
  scenario_badge: string;
  task: string;
  demo_wallet: string;
  can_approve: boolean;
  agent: {
    id: number;
    name: string;
    balance: number;
  };
}

export const CATEGORY_LABELS: Record<string, string> = {
  api: "APIs",
  compute: "Compute",
  data: "Data",
  agent: "Other agents",
  trading: "Trading",
};

export const CATEGORY_VALUES = ["api", "compute", "data", "agent", "trading"];

export const TX_STATUS_LABELS: Record<string, string> = {
  pending: "Pending",
  approved: "Approval Required",
  rejected: "Blocked",
  executed: "Completed",
  failed: "Failed",
};

export const TX_STATUS_TONES: Record<string, "success" | "destructive" | "warning" | "info" | "neutral"> = {
  executed: "success",
  approved: "info",
  pending: "warning",
  rejected: "destructive",
  failed: "destructive",
};

export const AGENT_STATUS_LABELS: Record<string, string> = {
  active: "ACTIVE",
  suspended: "SUSPENDED",
  killed: "KILLED",
};

export const AGENT_STATUS_TONES: Record<string, "success" | "warning" | "destructive"> = {
  active: "success",
  suspended: "warning",
  killed: "destructive",
};

export type PermissionKey =
  | "api"
  | "compute"
  | "data"
  | "agent"
  | "trading"
  | "human_transfers"
  | "withdrawals"
  | "contracts";

export interface PermissionDef {
  key: PermissionKey;
  label: string;
  description: string;
  category?: string;
  block?: "human_transfers" | "withdrawals" | "contracts";
}

export const PERMISSIONS: PermissionDef[] = [
  { key: "api", label: "API payments", description: "Pay API, RPC and infrastructure providers" },
  { key: "compute", label: "Compute", description: "Buy compute / server resources" },
  { key: "data", label: "Data", description: "Purchase market data and datasets" },
  { key: "agent", label: "Agent payments", description: "Send USDC to trusted peer agents" },
  { key: "trading", label: "Trading", description: "Execute swap / order tool actions" },
  { key: "human_transfers", label: "Human transfers", description: "Transfer USDC to human wallets", block: "human_transfers" },
  { key: "withdrawals", label: "Withdrawals", description: "Move funds out of agent escrow", block: "withdrawals" },
  { key: "contracts", label: "Contract interactions", description: "Call arbitrary smart contracts", block: "contracts" },
];

export type ActivityType =
  | "request"
  | "policy_allowed"
  | "policy_blocked"
  | "payment_completed"
  | "payment_failed"
  | "agent_created"
  | "agent_funded"
  | "policy_updated"
  | "task_started"
  | "approval_required"
  | "agent_paused"
  | "system";

export interface ActivityCheck {
  name: string;
  passed: boolean;
}

export interface ActivityEvent {
  id: string;
  timestamp: number;
  type: ActivityType;
  agentName: string;
  amount?: number;
  currency?: string;
  label?: string;
  detail?: string;
  checks?: ActivityCheck[];
  signature?: string | null;
  simulated?: boolean;
}

export interface ApprovalRequest {
  id: string;
  agentName: string;
  agentId?: number;
  amount: number;
  currency: string;
  reason: string;
  policyNote: string;
  recipient?: string;
  recipientName?: string;
  category?: string;
  expiresAt: number;
  transactionId?: number;
  simulated?: boolean;
  status: "pending" | "approved" | "rejected" | "expired";
}