import type {
  Agent,
  ConfigStatus,
  DemoResult,
  DemoScenario,
  DemoScenarioRunResult,
  LLMKeyMessage,
  LLMKeyStatus,
  MarketService,
  Policy,
  ScenarioId,
  ServicePaymentResult,
  ServiceRequestResult,
  TaskRunResult,
  Transaction,
} from "@/lib/types";
import { getAuthToken } from "@/lib/auth";
import { API_BASE, API_V1 } from "@/lib/api-config";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getAuthToken();
  const res = await fetch(`${API_BASE}${API_V1}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options?.headers || {}),
    },
    ...options,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || body.message || detail;
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  // Config / status
  getStatus: () => request<ConfigStatus>("/status"),

  // Wallet auth (nonce -> signed message -> JWT)
  authNonce: (walletAddress: string) =>
    request<{ wallet_address: string; nonce: string; message: string }>("/auth/nonce", {
      method: "POST",
      body: JSON.stringify({ wallet_address: walletAddress }),
    }),
  authVerify: (walletAddress: string, message: string, signature: string) =>
    request<{ access_token: string; token_type: string; wallet_address: string }>(
      "/auth/verify",
      {
        method: "POST",
        body: JSON.stringify({ wallet_address: walletAddress, message, signature }),
      }
    ),

  // Users
  ensureUser: (walletAddress: string) =>
    request<{ id: number; wallet_address: string }>("/users", {
      method: "POST",
      body: JSON.stringify({ wallet_address: walletAddress }),
    }),

  // End-user LLM API keys (Settings; stored encrypted on the backend)
  listLlmKeys: (wallet: string) =>
    request<LLMKeyStatus[]>(`/users/${wallet}/llm-keys`),
  setLlmKey: (wallet: string, provider: string, apiKey: string) =>
    request<LLMKeyMessage>(`/users/${wallet}/llm-keys/${provider}`, {
      method: "PUT",
      body: JSON.stringify({ api_key: apiKey }),
    }),
  deleteLlmKey: (wallet: string, provider: string) =>
    request<LLMKeyMessage>(`/users/${wallet}/llm-keys/${provider}`, {
      method: "DELETE",
    }),

  // Agents
  listAgents: (wallet: string) =>
    request<Agent[]>(`/users/${wallet}/agents`),
  getAgent: (wallet: string, agentId: number) =>
    request<Agent>(`/users/${wallet}/agents/${agentId}`),
  createAgent: (wallet: string, name: string, description?: string) =>
    request<Agent>(`/users/${wallet}/agents`, {
      method: "POST",
      body: JSON.stringify({ name, description }),
    }),
  fundAgent: (wallet: string, agentId: number, amount: number) =>
    request<FundResult>(`/users/${wallet}/agents/${agentId}/fund`, {
      method: "POST",
      body: JSON.stringify({ amount }),
    }),
  confirmFund: (wallet: string, agentId: number, amount: number, signature: string) =>
    request<Agent>(`/users/${wallet}/agents/${agentId}/fund/confirm`, {
      method: "POST",
      body: JSON.stringify({ amount, signature }),
    }),
  setPolicy: (wallet: string, agentId: number, policy: PolicyInput) =>
    request<Policy>(`/users/${wallet}/agents/${agentId}/policy`, {
      method: "POST",
      body: JSON.stringify(policy),
    }),
  updateAgentStatus: (wallet: string, agentId: number, status: string) =>
    request<Agent>(`/users/${wallet}/agents/${agentId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  killAgent: (wallet: string, agentId: number) =>
    request<{ message: string }>(`/users/${wallet}/agents/${agentId}`, {
      method: "DELETE",
    }),

  // Transactions
  listTransactions: (wallet: string) =>
    request<Transaction[]>(`/users/${wallet}/transactions`),
  getTransaction: (wallet: string, txId: number) =>
    request<Transaction>(`/users/${wallet}/transactions/${txId}`),
  approveTransaction: (wallet: string, txId: number) =>
    request<{ approved: boolean; executed: boolean; transaction: Transaction }>(
      `/users/${wallet}/transactions/${txId}/approve`,
      { method: "POST" }
    ),
  rejectTransaction: (wallet: string, txId: number) =>
    request<{ rejected: boolean; transaction: Transaction }>(
      `/users/${wallet}/transactions/${txId}/reject`,
      { method: "POST" }
    ),

  // Agent runs
  runTask: (wallet: string, agentId: number, task: string) =>
    request<TaskRunResult>(`/users/${wallet}/agents/${agentId}/runs`, {
      method: "POST",
      body: JSON.stringify({ task }),
    }),
  listRuns: (wallet: string, agentId: number) =>
    request<TaskRunResult[]>(`/users/${wallet}/agents/${agentId}/runs`),

  // Demo
  demoCheck: (payload: {
    agent_id: number;
    amount: number;
    recipient: string;
    recipient_name: string;
    category: string;
    description?: string;
  }) =>
    request<{
      decision: { allowed: boolean; reason: string; checks: unknown[] };
      transaction: Transaction;
      summary: { requested: number; per_transaction_limit: number | null; daily_limit: number | null; recipient: string; recipient_trusted: boolean };
    }>("/demo/check", { method: "POST", body: JSON.stringify(payload) }),

  // Marketplace / Service Directory
  listServices: () => request<MarketService[]>("/services"),
  getService: (serviceId: number) =>
    request<MarketService>(`/services/${serviceId}`),
  requestService: (serviceId: number, agentId: number) =>
    request<ServiceRequestResult>(`/services/${serviceId}/request`, {
      method: "POST",
      body: JSON.stringify({ agent_id: agentId }),
    }),
  payForService: (
    serviceId: number,
    agentId: number,
    requestedAmount?: number
  ) =>
    request<ServicePaymentResult>(`/services/${serviceId}/payment`, {
      method: "POST",
      body: JSON.stringify({ agent_id: agentId, requested_amount: requestedAmount }),
    }),
  getServiceResult: (serviceId: number, agentId: number, proof?: { tx_hash: string }) =>
    request<Record<string, unknown>>(`/services/${serviceId}/result`, {
      method: "POST",
      body: JSON.stringify({ agent_id: agentId, proof: proof ?? null }),
    }),
  runKillerDemo: (agentId: number, amount = 0.02) =>
    request<DemoResult>("/services/demo/killer", {
      method: "POST",
      body: JSON.stringify({ agent_id: agentId, requested_amount: amount }),
    }),
  runFailedDemo: (agentId: number, amount = 50) =>
    request<DemoResult>("/services/demo/failed", {
      method: "POST",
      body: JSON.stringify({ agent_id: agentId, requested_amount: amount }),
    }),

  // One-click demo scenarios (DEMO_MODE gate moves all money as simulated USDC)
  listDemoScenarios: () =>
    request<{ demo_mode: boolean; scenarios: DemoScenario[] }>("/demo/scenarios"),
  runDemoScenario: (scenario: ScenarioId, clientRequestId?: string) =>
    request<DemoScenarioRunResult>(`/demo/scenarios/${scenario}/run`, {
      method: "POST",
      body: JSON.stringify({ client_request_id: clientRequestId ?? null }),
    }),
  approveDemoScenario: (scenario: ScenarioId, clientRequestId?: string) =>
    request<DemoScenarioRunResult>(`/demo/scenarios/${scenario}/approve`, {
      method: "POST",
      body: JSON.stringify({ client_request_id: clientRequestId ?? null }),
    }),
};

export interface PolicyInput {
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

export interface PaymentFee {
  fee_sol: number;
  fee_lamports: number;
  currency: string;
  estimated?: boolean;
}

export interface PaymentRequest {
  request_id: string;
  mode: string;
  network: string;
  simulated: boolean;
  from_address: string;
  to_address: string;
  to_ata?: string;
  amount: number;
  currency: string;
  mint: string;
  decimals: number;
  fee: PaymentFee;
  signature?: string | null;
  explorer_url?: string | null;
  created_at?: string;
  expires_at?: string;
}

export interface FundMockResult {
  mode: "mock";
  simulated: true;
  tx_hash: string;
  agent: Agent;
}

export interface FundSolanaResult {
  mode: "solana";
  simulated: false;
  agent_id: number;
  agent_name: string;
  payment_request: PaymentRequest;
}

export type FundResult = FundMockResult | FundSolanaResult;