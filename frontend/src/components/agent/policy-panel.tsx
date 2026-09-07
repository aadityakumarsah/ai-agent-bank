"use client";

import { useEffect, useState } from "react";
import { Shield, Loader2, Check, Save } from "lucide-react";
import type { Policy } from "@/lib/types";
import { PERMISSIONS, type PermissionKey } from "@/lib/types";
import type { PolicyInput } from "@/lib/api";
import { Toggle } from "@/components/ui/toggle";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Panel } from "@/components/ui/panel";
import { permissionRecord } from "@/lib/policy";

export function PolicyPanel({
  current,
  onApply,
}: {
  current: Policy | null;
  onApply: (p: PolicyInput) => Promise<void>;
}) {
  const [maxPerTx, setMaxPerTx] = useState("20");
  const [maxPerDay, setMaxPerDay] = useState("100");
  const [maxPerMonth, setMaxPerMonth] = useState("1000");
  const [approvalAbove, setApprovalAbove] = useState("50");
  const [permissions, setPermissions] = useState<Record<string, boolean>>(() =>
    permissionRecord(null)
  );
  const [trusted, setTrusted] = useState("rpcProvider, apiProvider, dataProvider, agentPeer");
  const [saving, setSaving] = useState(false);
  const [savedFlash, setSavedFlash] = useState(false);

  useEffect(() => {
    if (current) {
      setMaxPerTx(String(current.max_per_transaction));
      setMaxPerDay(String(current.max_per_day));
      setMaxPerMonth(
        current.max_per_month != null ? String(current.max_per_month) : ""
      );
      setApprovalAbove(
        current.require_approval_above != null ? String(current.require_approval_above) : ""
      );
      setPermissions(permissionRecord(current));
      setTrusted(current.allowed_recipient_addresses?.join(", ") ?? "");
    }
  }, [current]);

  const toggle = (key: string) =>
    setPermissions((prev) => ({ ...prev, [key]: !prev[key] }));

  const submit = async () => {
    setSaving(true);
    try {
      await onApply({
        max_per_transaction: parseFloat(maxPerTx) || 0,
        max_per_day: parseFloat(maxPerDay) || 0,
        max_per_month: parseFloat(maxPerMonth) || null,
        allowed_categories: ["api", "compute", "data", "agent", "trading"].filter(
          (c) => permissions[c]
        ),
        blocked_human_transfers: !permissions.human_transfers,
        blocked_withdrawals: !permissions.withdrawals,
        blocked_arbitrary_contracts: !permissions.contracts,
        require_approval_above: parseFloat(approvalAbove) || null,
        allowed_recipient_addresses: trusted
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      });
      setSavedFlash(true);
      setTimeout(() => setSavedFlash(false), 2000);
    } finally {
      setSaving(false);
    }
  };

  const perTx = parseFloat(maxPerTx) || 0;
  const perDay = parseFloat(maxPerDay) || 0;

  return (
    <div className="flex flex-col gap-6">
      {/* Limits */}
      <Panel
        title="Limits"
        description="Hard numbers the policy engine enforces on every transaction"
      >
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Input
            id="ptx"
            label="Transaction limit"
            type="number"
            min="0"
            prefix="$"
            value={maxPerTx}
            onChange={(e) => setMaxPerTx(e.target.value)}
          />
          <Input
            id="pday"
            label="Daily limit"
            type="number"
            min="0"
            prefix="$"
            value={maxPerDay}
            onChange={(e) => setMaxPerDay(e.target.value)}
          />
          <Input
            id="pmonth"
            label="Monthly limit"
            type="number"
            min="0"
            prefix="$"
            placeholder="Unlimited"
            value={maxPerMonth}
            onChange={(e) => setMaxPerMonth(e.target.value)}
          />
          <Input
            id="papprove"
            label="Approval threshold"
            type="number"
            min="0"
            prefix="$"
            placeholder="Off"
            value={approvalAbove}
            onChange={(e) => setApprovalAbove(e.target.value)}
          />
        </div>
      </Panel>

      {/* Permissions */}
      <Panel
        title="Permissions"
        description="What the agent is allowed to do. Blocked actions always deny — deterministically, in code."
      >
        <div className="flex flex-col gap-1.5">
          {PERMISSIONS.map((perm) => (
            <div
              key={perm.key}
              className="flex items-center justify-between gap-4 rounded-lg border border-border/70 bg-background/30 px-3 py-2.5"
            >
              <div className="min-w-0">
                <div className="text-sm font-medium text-foreground">{perm.label}</div>
                <div className="text-xs text-muted-foreground">{perm.description}</div>
              </div>
              <div className="flex shrink-0 items-center gap-2.5">
                <span
                  className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                    permissions[perm.key]
                      ? "bg-success/15 text-success"
                      : "bg-muted text-muted-foreground"
                  }`}
                >
                  {permissions[perm.key] ? "ON" : "OFF"}
                </span>
                <Toggle
                  sizing="sm"
                  checked={!!permissions[perm.key]}
                  onCheckedChange={() => toggle(perm.key as PermissionKey)}
                />
              </div>
            </div>
          ))}
        </div>
      </Panel>

      {/* Trusted recipients */}
      <Panel
        title="Trusted recipients"
        description="Whitelist of encrypted wallet IDs / merchant identifiers the agent may pay"
      >
        <Input
          id="ptrusted"
          label="Recipient whitelist (comma separated)"
          value={trusted}
          onChange={(e) => setTrusted(e.target.value)}
          placeholder="rpcProvider, apiProvider, dataProvider, agentPeer"
        />
        <div className="mt-2 text-xs text-muted-foreground">
          Payments to anything not on this list require approval — or are blocked outright.
        </div>
      </Panel>

      <div className="flex items-center gap-3">
        <Button onClick={submit} disabled={saving || !perTx || !perDay} className="min-w-40">
          {saving ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : savedFlash ? (
            <Check className="h-4 w-4" />
          ) : (
            <Save className="h-4 w-4" />
          )}
          {saving ? "Applying policy…" : savedFlash ? "Policy applied" : "Apply policy"}
        </Button>
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Shield className="h-3.5 w-3.5 text-primary" />
          Enforced before any payment executes
        </div>
      </div>
    </div>
  );
}