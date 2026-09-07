"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Shield, ShieldOff, ArrowRight } from "lucide-react";
import { useBankData } from "@/hooks/use-bank-data";
import { PageHeader } from "@/components/layout/page-header";
import { Panel } from "@/components/ui/panel";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { AgentStatusBadge } from "@/components/ui/status-badge";
import { PermissionChip } from "@/components/policies/permission-chip";
import { PERMISSIONS, type PermissionKey } from "@/lib/types";
import { permissionEnabled } from "@/lib/policy";
import { formatUsdc } from "@/lib/utils";

export function PoliciesPage() {
  const router = useRouter();
  const { agents, loading, error, load } = useBankData();

  const withPolicy = agents.filter((a) => a.policies);
  const withoutPolicy = agents.filter((a) => !a.policies);

  if (loading && agents.length === 0) {
    return (
      <div className="flex flex-col gap-6">
        <div className="h-7 w-32 animate-pulse rounded bg-muted" />
        <div className="flex flex-col gap-4">
          {[0, 1].map((i) => (
            <div key={i} className="h-40 animate-pulse rounded-xl bg-muted/40" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Policies"
        description="Deterministic permission rules for every agent. The AI can never bypass these — they are enforced in code, before any payment."
      />

      {error && <ErrorState description={error} onRetry={() => void load()} />}

      {withPolicy.length > 0 && (
        <div className="flex flex-col gap-4">
          {withPolicy.map((agent) => {
            const p = agent.policies!;
            return (
              <Panel
                key={agent.id}
                title={
                  <div className="flex items-center gap-2">
                    {agent.name}
                    <AgentStatusBadge status={agent.status} />
                  </div>
                }
                description={`Policy applied to agent #${agent.id} — enforceable by the policy engine before every transaction.`}
                action={
                  <Link href={`/agents/${agent.id}?tab=policy`}>
                    <Button variant="outline" size="sm" className="h-8 text-xs">
                      Edit policy <ArrowRight className="h-3 w-3" />
                    </Button>
                  </Link>
                }
              >
                <div className="grid grid-cols-1 gap-6 xl:grid-cols-5">
                  {/* Limits */}
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:col-span-2">
                    <LimitCell label="Transaction limit" value={`≤ ${formatUsdc(p.max_per_transaction)}`} />
                    <LimitCell label="Daily limit" value={`≤ ${formatUsdc(p.max_per_day)}`} />
                    <LimitCell
                      label="Monthly limit"
                      value={
                        p.max_per_month != null
                          ? `≤ ${formatUsdc(p.max_per_month)}`
                          : "Unlimited"
                      }
                      hint="Enforced over a rolling 30 days"
                    />
                    <LimitCell
                      label="Approval threshold"
                      value={
                        p.require_approval_above != null
                          ? `> ${formatUsdc(p.require_approval_above)}`
                          : "Always approve"
                      }
                    />
                  </div>
                  {/* Permissions */}
                  <div className="xl:col-span-3">
                    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-2">
                      {PERMISSIONS.map((perm) => (
                        <PermissionChip
                          key={perm.key}
                          permission={perm}
                          enabled={permissionEnabled(p, perm.key as PermissionKey)}
                        />
                      ))}
                    </div>
                    {p.allowed_recipient_addresses.length > 0 && (
                      <div className="mt-3">
                        <div className="mb-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                          Trusted recipients
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {p.allowed_recipient_addresses.map((r) => (
                            <span
                              key={r}
                              className="rounded border border-border bg-card px-2 py-0.5 font-mono text-[10px] text-muted-foreground"
                            >
                              {r}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </Panel>
            );
          })}
        </div>
      )}

      {withoutPolicy.length > 0 && (
        <Panel title="Agents without a policy" description="These agents cannot spend until you set their policy.">
          <div className="flex flex-col divide-y divide-border/60">
            {withoutPolicy.map((agent) => (
              <div key={agent.id} className="flex items-center justify-between gap-3 py-3">
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-secondary text-warning">
                    <ShieldOff className="h-4 w-4" />
                  </div>
                  <div>
                    <div className="text-sm font-medium text-foreground">{agent.name}</div>
                    <div className="text-xs text-muted-foreground">
                      No spending rules defined
                    </div>
                  </div>
                </div>
                <Button
                  variant="secondary"
                  size="sm"
                  className="h-8 text-xs"
                  onClick={() => router.push(`/agents/${agent.id}?tab=policy`)}
                >
                  <Shield className="h-3.5 w-3.5" />
                  Set policy
                </Button>
              </div>
            ))}
          </div>
        </Panel>
      )}

      {agents.length === 0 && (
        <Panel>
          <EmptyState
            icon={Shield}
            title="No policies yet"
            description="Create an agent and define its spending permissions to see policies here."
            actionLabel="Create agent"
            onAction={() => router.push("/agents/new")}
          />
        </Panel>
      )}
    </div>
  );
}

function LimitCell({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-lg border border-border bg-background/40 px-3 py-2.5">
      <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 text-sm font-semibold tabular-nums text-foreground">{value}</div>
      {hint && <div className="mt-0.5 text-[10px] text-muted-foreground">{hint}</div>}
    </div>
  );
}