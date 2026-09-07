import type { Policy, PermissionKey } from "@/lib/types";
import type { PolicyInput } from "@/lib/api";

export function permissionEnabled(policy: Policy | null | undefined, key: PermissionKey): boolean {
  if (!policy) return false;
  const cats = new Set(policy.allowed_categories ?? []);
  switch (key) {
    case "api":
      return cats.has("api");
    case "compute":
      return cats.has("compute");
    case "data":
      return cats.has("data");
    case "agent":
      return cats.has("agent");
    case "trading":
      return cats.has("trading");
    case "human_transfers":
      return !policy.blocked_human_transfers;
    case "withdrawals":
      return !policy.blocked_withdrawals;
    case "contracts":
      return !policy.blocked_arbitrary_contracts;
    default:
      return false;
  }
}

export function policyFromState(state: {
  maxPerTx: number;
  maxPerDay: number;
  maxPerMonth: number | null;
  approvalAbove: number | null;
  permissions: Record<string, boolean>;
  trusted: string[];
}): PolicyInput {
  const cats = ["api", "compute", "data", "agent", "trading"].filter(
    (c) => state.permissions[c]
  );
  return {
    max_per_transaction: state.maxPerTx,
    max_per_day: state.maxPerDay,
    max_per_month: state.maxPerMonth,
    allowed_categories: cats,
    blocked_human_transfers: !state.permissions.human_transfers,
    blocked_withdrawals: !state.permissions.withdrawals,
    blocked_arbitrary_contracts: !state.permissions.contracts,
    require_approval_above: state.approvalAbove,
    allowed_recipient_addresses: state.trusted,
  };
}

export function monthlyLimit(policy: Policy | null | undefined): number | null {
  if (!policy) return null;
  if (policy.max_per_month != null) return policy.max_per_month;
  return policy.max_per_day * 30;
}

export function permissionRecord(policy: Policy | null | undefined): Record<string, boolean> {
  return {
    api: permissionEnabled(policy, "api"),
    compute: permissionEnabled(policy, "compute"),
    data: permissionEnabled(policy, "data"),
    agent: permissionEnabled(policy, "agent"),
    trading: permissionEnabled(policy, "trading"),
    human_transfers: permissionEnabled(policy, "human_transfers"),
    withdrawals: permissionEnabled(policy, "withdrawals"),
    contracts: permissionEnabled(policy, "contracts"),
  };
}