"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Loader2,
  ArrowLeft,
  ArrowRight,
  Check,
  Bot,
  CheckCircle2,
  Sparkles,
} from "lucide-react";
import { useWalletConnection } from "@/components/wallet/wallet-context";
import { api } from "@/lib/api";
import { SUGGESTED_AGENTS } from "@/lib/demo";
import { PERMISSIONS, type PermissionKey } from "@/lib/types";
import { Stepper } from "@/components/ui/stepper";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Toggle } from "@/components/ui/toggle";
import { Panel } from "@/components/ui/panel";
import { useToast } from "@/components/ui/toast";
import { formatUsdc } from "@/lib/utils";
import { cn } from "@/lib/utils";

const STEPS = ["Name", "Description", "Budget", "Permissions", "Review"];

const DEFAULT_PERMISSIONS: Record<string, boolean> = {
  api: true,
  compute: true,
  data: true,
  agent: true,
  trading: false,
  human_transfers: false,
  withdrawals: false,
  contracts: false,
};

export function CreateAgentWizard() {
  const { address } = useWalletConnection();
  const router = useRouter();
  const { toast } = useToast();

  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [budget, setBudget] = useState("500");
  const [maxPerTx, setMaxPerTx] = useState("20");
  const [maxPerDay, setMaxPerDay] = useState("100");
  const [maxPerMonth, setMaxPerMonth] = useState("1000");
  const [approvalAbove, setApprovalAbove] = useState("20");
  const [permissions, setPermissions] = useState<Record<string, boolean>>(DEFAULT_PERMISSIONS);
  const [trusted, setTrusted] = useState("rpcProvider, apiProvider, dataProvider, agentPeer");

  const [creating, setCreating] = useState(false);
  const [createdAgentId, setCreatedAgentId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const togglePerm = (key: PermissionKey) => {
    setPermissions((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const canContinue = () => {
    if (step === 0) return name.trim().length > 0;
    if (step === 2) {
      return (
        (parseFloat(budget) || 0) > 0 &&
        (parseFloat(maxPerTx) || 0) > 0 &&
        (parseFloat(maxPerDay) || 0) > 0
      );
    }
    return true;
  };

  const createAgent = async () => {
    if (!address) return;
    setCreating(true);
    setError(null);
    try {
      const agent = await api.createAgent(address, name.trim(), description.trim() || undefined);
      await api.setPolicy(address, agent.id, {
        max_per_transaction: parseFloat(maxPerTx) || 0,
        max_per_day: parseFloat(maxPerDay) || 0,
        max_per_month: parseFloat(maxPerMonth) || null,
        allowed_categories: ["api", "compute", "data", "agent", "trading"].filter((c) => permissions[c]),
        blocked_human_transfers: !permissions.human_transfers,
        blocked_withdrawals: !permissions.withdrawals,
        blocked_arbitrary_contracts: !permissions.contracts,
        require_approval_above: parseFloat(approvalAbove) || null,
        allowed_recipient_addresses: trusted
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      });
      if ((parseFloat(budget) || 0) > 0) {
        await api.fundAgent(address, agent.id, parseFloat(budget));
      }
      setCreatedAgentId(agent.id);
      toast({
        type: "success",
        title: "Agent created",
        description: `${name.trim()} is funded and policy-locked, ready for tasks.`,
      });
    } catch (e) {
      const message = e instanceof Error ? e.message : "Failed to create agent";
      setError(message);
      toast({ type: "error", title: "Could not create agent", description: message });
    } finally {
      setCreating(false);
    }
  };

  if (createdAgentId != null) {
    return (
      <div className="mx-auto flex max-w-md flex-col items-center gap-5 py-10 text-center animate-fade-up">
        <div className="flex h-16 w-16 items-center justify-center rounded-full border border-success/30 bg-success/10 text-success">
          <CheckCircle2 className="h-8 w-8" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-foreground">Agent deployed</h2>
          <p className="mt-1.5 text-sm text-muted-foreground">
            <span className="font-medium text-foreground">{name.trim()}</span> is now funded
            with <span className="tabular-nums">{formatUsdc(parseFloat(budget))}</span> USDC and
            protected by its policy. It proposes — the engine decides.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" onClick={() => router.push("/agents")}>
            Agents
          </Button>
          <Button onClick={() => router.push(`/agents/${createdAgentId}`)}>
            <Bot className="h-4 w-4" />
            Manage {name.trim()}
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <div>
        <Stepper steps={STEPS} current={step} />
      </div>

      <div className="animate-fade-up">
        {step === 0 && (
          <NameStep name={name} setName={setName} />
        )}
        {step === 1 && (
          <DescriptionStep description={description} setDescription={setDescription} />
        )}
        {step === 2 && (
          <BudgetStep
            budget={budget}
            setBudget={setBudget}
            maxPerTx={maxPerTx}
            setMaxPerTx={setMaxPerTx}
            maxPerDay={maxPerDay}
            setMaxPerDay={setMaxPerDay}
            maxPerMonth={maxPerMonth}
            setMaxPerMonth={setMaxPerMonth}
            approvalAbove={approvalAbove}
            setApprovalAbove={setApprovalAbove}
          />
        )}
        {step === 3 && (
          <PermissionsStep permissions={permissions} toggle={togglePerm} trusted={trusted} setTrusted={setTrusted} />
        )}
        {step === 4 && (
          <ReviewStep
            name={name}
            description={description}
            budget={budget}
            maxPerTx={maxPerTx}
            maxPerDay={maxPerDay}
            maxPerMonth={maxPerMonth}
            approvalAbove={approvalAbove}
            permissions={permissions}
          />
        )}
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="flex items-center justify-between border-t border-border pt-5">
        <Button variant="ghost" disabled={step === 0 || creating} onClick={() => setStep((s) => s - 1)}>
          <ArrowLeft className="h-4 w-4" />
          Back
        </Button>

        {step < STEPS.length - 1 ? (
          <Button disabled={!canContinue()} onClick={() => setStep((s) => s + 1)}>
            Continue
            <ArrowRight className="h-4 w-4" />
          </Button>
        ) : (
          <Button onClick={createAgent} disabled={creating || !canContinue()} className="min-w-56">
            {creating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            {creating ? "Deploying agent…" : "Create Agent"}
          </Button>
        )}
      </div>
    </div>
  );
}

function NameStep({ name, setName }: { name: string; setName: (v: string) => void }) {
  return (
    <Panel
      title="Name your agent"
      description="A short, descriptive name you'll recognize in activity and spending."
      bodyClassName="flex flex-col gap-4"
    >
      <Input
        id="agent-name"
        label="Agent name"
        placeholder="e.g. ResearchBot"
        value={name}
        onChange={(e) => setName(e.target.value)}
        autoFocus
      />
      <div className="flex flex-wrap gap-1.5">
        {SUGGESTED_AGENTS.map((s) => (
          <button
            key={s.name}
            onClick={() => {
              setName(s.name);
            }}
            className="rounded-full border border-border bg-card px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
          >
            {s.name}
          </button>
        ))}
      </div>
    </Panel>
  );
}

function DescriptionStep({
  description,
  setDescription,
}: {
  description: string;
  setDescription: (v: string) => void;
}) {
  return (
    <Panel
      title="Describe its job"
      description="What is this agent for? Shown when you review the agent."
      bodyClassName="flex flex-col gap-3"
    >
      <Textarea
        id="agent-desc"
        label="Description"
        placeholder="e.g. Autonomous research assistant that finds and tests Solana RPC providers."
        rows={4}
        value={description}
        onChange={(e) => setDescription(e.target.value)}
      />
      <div className="max-h-36 overflow-y-auto space-y-1.5">
        {SUGGESTED_AGENTS.map((s) => (
          <button
            key={s.name}
            onClick={() => setDescription(s.description)}
            className="block w-full rounded-lg border border-border bg-background/30 px-3 py-2 text-left text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
          >
            <span className="font-medium text-foreground">{s.name}</span> — {s.description}
          </button>
        ))}
      </div>
    </Panel>
  );
}

function BudgetStep({
  budget,
  setBudget,
  maxPerTx,
  setMaxPerTx,
  maxPerDay,
  setMaxPerDay,
  maxPerMonth,
  setMaxPerMonth,
  approvalAbove,
  setApprovalAbove,
}: {
  budget: string;
  setBudget: (v: string) => void;
  maxPerTx: string;
  setMaxPerTx: (v: string) => void;
  maxPerDay: string;
  setMaxPerDay: (v: string) => void;
  maxPerMonth: string;
  setMaxPerMonth: (v: string) => void;
  approvalAbove: string;
  setApprovalAbove: (v: string) => void;
}) {
  return (
    <Panel
      title="Set the budget"
      description="Funding is a hard ceiling from the wallets you control. The agent can never exceed it."
      bodyClassName="flex flex-col gap-4"
    >
      <Input
        id="budget"
        label="Total funding"
        type="number"
        min="0"
        prefix="$"
        value={budget}
        onChange={(e) => setBudget(e.target.value)}
        hint="USDC moved into the agent escrow"
      />
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Input
          id="budget-tx"
          label="Transaction limit"
          type="number"
          min="0"
          prefix="$"
          value={maxPerTx}
          onChange={(e) => setMaxPerTx(e.target.value)}
          hint="Max per request"
        />
        <Input
          id="budget-day"
          label="Daily limit"
          type="number"
          min="0"
          prefix="$"
          value={maxPerDay}
          onChange={(e) => setMaxPerDay(e.target.value)}
          hint="Max per day"
        />
        <Input
          id="budget-month"
          label="Monthly limit"
          type="number"
          min="0"
          prefix="$"
          placeholder="Unlimited"
          value={maxPerMonth}
          onChange={(e) => setMaxPerMonth(e.target.value)}
          hint="Max per 30 days"
        />
        <Input
          id="budget-approve"
          label="Approval threshold"
          type="number"
          min="0"
          prefix="$"
          value={approvalAbove}
          onChange={(e) => setApprovalAbove(e.target.value)}
          hint="Human approval above"
        />
      </div>
    </Panel>
  );
}

function PermissionsStep({
  permissions,
  toggle,
  trusted,
  setTrusted,
}: {
  permissions: Record<string, boolean>;
  toggle: (key: PermissionKey) => void;
  trusted: string;
  setTrusted: (v: string) => void;
}) {
  return (
    <Panel
      title="Permissions"
      description="What this agent is allowed to do with money. Everything here is deterministic — the AI cannot override it."
      bodyClassName="flex flex-col gap-4"
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
                className={cn(
                  "rounded px-1.5 py-0.5 text-[10px] font-bold",
                  permissions[perm.key]
                    ? "bg-success/15 text-success"
                    : "bg-muted text-muted-foreground"
                )}
              >
                {permissions[perm.key] ? "ON" : "OFF"}
              </span>
              <Toggle
                sizing="sm"
                checked={!!permissions[perm.key]}
                onCheckedChange={() => toggle(perm.key)}
              />
            </div>
          </div>
        ))}
      </div>
      <Input
        id="wiz-trusted"
        label="Trusted recipients"
        value={trusted}
        onChange={(e) => setTrusted(e.target.value)}
        placeholder="rpcProvider, apiProvider, dataProvider, agentPeer"
      />
    </Panel>
  );
}

function ReviewStep({
  name,
  description,
  budget,
  maxPerTx,
  maxPerDay,
  maxPerMonth,
  approvalAbove,
  permissions,
}: {
  name: string;
  description: string;
  budget: string;
  maxPerTx: string;
  maxPerDay: string;
  maxPerMonth: string;
  approvalAbove: string;
  permissions: Record<string, boolean>;
}) {
  const displayName = name.trim() || "Your agent";
  const amount = parseFloat(budget) || 0;
  const tx = parseFloat(maxPerTx) || 0;
  const day = parseFloat(maxPerDay) || 0;
  const month = parseFloat(maxPerMonth) || 0;
  const approve = parseFloat(approvalAbove) || 0;

  return (
    <Panel
      title={<span className="flex items-center gap-2"><Check className="h-4 w-4 text-primary" />Review</span>}
      description="Everything the agent will be funded with and allowed to do once you create it."
      bodyClassName="flex flex-col gap-5"
    >
      <div className="flex items-center gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-secondary text-primary">
          <Bot className="h-6 w-6" />
        </div>
        <div>
          <div className="text-lg font-bold text-foreground">{displayName}</div>
          <div className="text-xs text-muted-foreground">
            {description.trim() || "No description"}
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-primary/25 bg-primary/[0.05] p-4">
        <div className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
          You&apos;re giving {displayName}
        </div>
        <div className="mt-1 text-3xl font-bold tracking-tight tabular-nums text-primary">
          {formatUsdc(amount)} <span className="text-base font-medium text-muted-foreground">USDC</span>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <Chip label="Transaction limit" value={`${formatUsdc(tx)}`} />
          <Chip label="Daily limit" value={`${formatUsdc(day)}`} />
          {approve > 0 && <Chip label="Approve above" value={`${formatUsdc(approve)}`} />}
          {month > 0 && <Chip label="Monthly limit" value={`${formatUsdc(month)}`} />}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
        {PERMISSIONS.map((perm) => (
          <div key={perm.key} className="flex items-center justify-between rounded-lg border border-border/70 bg-background/30 px-3 py-2">
            <span className="text-sm text-foreground">{perm.label}</span>
            <span
              className={cn(
                "rounded px-1.5 py-0.5 text-[10px] font-bold tracking-wide",
                permissions[perm.key]
                  ? "bg-success/15 text-success"
                  : "bg-muted text-muted-foreground"
              )}
            >
              {permissions[perm.key] ? "ON" : "OFF"}
            </span>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function Chip({ label, value }: { label: string; value: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-2.5 py-1 text-xs">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-semibold tabular-nums text-foreground">{value}</span>
    </span>
  );
}