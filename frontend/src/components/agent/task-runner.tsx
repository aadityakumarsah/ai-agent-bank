"use client";

import { useState } from "react";
import {
  Loader2,
  Play,
  ShieldCheck,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  Terminal,
  ExternalLink,
  Inbox,
  ThumbsUp,
  ThumbsDown,
} from "lucide-react";
import type { Agent, TaskRunResult } from "@/lib/types";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Panel } from "@/components/ui/panel";
import { formatUsdc, cn, shortAddress } from "@/lib/utils";
import { isSimulatedSignature, explorerUrlForSignature } from "@/lib/solana";
import { useToast } from "@/components/ui/toast";

const demoTasks = [
  "Research the best Solana RPC provider and test their API.",
  "Transfer $300 to an unknown wallet",
  "Buy a market data feed for my trading strategy.",
];

export function TaskRunner({
  agent,
  address,
  onTransaction,
}: {
  agent: Agent;
  address: string;
  onTransaction: () => void;
}) {
  const { toast } = useToast();
  const [task, setTask] = useState(demoTasks[0]);
  const [running, setRunning] = useState(false);
  const [deciding, setDeciding] = useState(false);
  const [result, setResult] = useState<TaskRunResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    if (!task.trim() || !address) return;
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.runTask(address, agent.id, task);
      setResult(res);
      onTransaction();
      if (res.decision?.requires_approval) {
        toast({
          type: "info",
          title: "Approval required",
          description: `The payment is paused — approve or reject it to decide.`,
        });
      } else if (res.blocked) {
        toast({
          type: "error",
          title: "Transaction blocked",
          description: "The policy engine denied this payment before it could execute.",
        });
      } else if (res.transaction) {
        toast({
          type: "success",
          title: "Payment executed",
          description: `${formatUsdc(res.transaction.amount)} ${res.transaction.currency} sent.`,
        });
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Task failed");
    } finally {
      setRunning(false);
    }
  };

  const decide = async (action: "approve" | "reject") => {
    const tx = result?.transaction;
    if (!tx || !address) return;
    setDeciding(true);
    setError(null);
    try {
      if (action === "approve") {
        const res = await api.approveTransaction(address, tx.id);
        const settled = res.transaction;
        setResult({
          ...result!,
          status: settled.status,
          decision: result!.decision,
          transaction: settled,
          blocked: false,
          approval_required: false,
        });
        toast({
          type: res.executed ? "success" : "info",
          title: res.executed ? "Payment approved and executed" : "Payment already processed",
          description:
            res.executed
              ? `${formatUsdc(settled.amount)} ${settled.currency} sent via the policy engine.`
              : "Nothing to execute — the payment was already settled.",
        });
      } else {
        const res = await api.rejectTransaction(address, tx.id);
        const set = res.transaction;
        setResult({
          ...result!,
          status: set.status,
          transaction: set,
          approval_required: false,
        });
        toast({
          type: "info",
          title: "Payment rejected",
          description: "The payment was refused — no money moved.",
        });
      }
      onTransaction();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Decision failed");
    } finally {
      setDeciding(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-1.5">
        {demoTasks.map((t) => (
          <button
            key={t}
            onClick={() => {
              setTask(t);
              setResult(null);
            }}
            className={cn(
              "rounded-full border px-3 py-1.5 text-xs transition-colors",
              task === t
                ? "border-primary/40 bg-primary/10 text-primary"
                : "border-border bg-card text-muted-foreground hover:text-foreground"
            )}
          >
            {t.length > 38 ? t.slice(0, 38) + "…" : t}
          </button>
        ))}
      </div>

      <Textarea
        id="task"
        label="Task prompt"
        value={task}
        onChange={(e) => {
          setTask(e.target.value);
          setResult(null);
        }}
        rows={3}
      />

      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2.5 text-sm text-destructive">
          {error}
        </div>
      )}

      <Button
        onClick={run}
        disabled={running || !task.trim() || agent.status !== "active"}
        className="w-full"
      >
        {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
        {running
          ? "Agent is working…"
          : agent.status === "active"
            ? "Run task"
            : "Agent is not active"}
      </Button>

      {result && <RunResult result={result} deciding={deciding} onDecide={decide} />}
    </div>
  );
}

function RunResult({
  result,
  deciding,
  onDecide,
}: {
  result: TaskRunResult;
  deciding: boolean;
  onDecide: (action: "approve" | "reject") => void;
}) {
  if (result.blocked) return <BlockedRun result={result} />;
  if (result.error) return <FailedRun result={result} />;
  if (result.transaction?.status === "rejected") return <RejectedRun result={result} />;
  if (result.decision?.requires_approval && !result.decision?.allowed && result.approval_required !== false) {
    return <ApprovalRun result={result} deciding={deciding} onDecide={onDecide} />;
  }
  return <SuccessRun result={result} />;
}

function BlockedRun({ result }: { result: TaskRunResult }) {
  const tx = result.transaction;
  const decision = result.decision;
  return (
    <div className="overflow-hidden rounded-xl border border-destructive/40 bg-destructive/[0.04] animate-fade-up">
      <div className="flex items-center gap-2 bg-destructive/10 px-4 py-2.5">
        <ShieldAlert className="h-4 w-4 text-destructive" />
        <div className="text-sm font-bold tracking-wide text-destructive">
          TRANSACTION BLOCKED
        </div>
      </div>
      <div className="flex flex-col gap-3 p-4">
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-lg border border-border bg-card p-3">
            <div className="text-xs text-muted-foreground">Requested</div>
            <div className="text-lg font-bold tabular-nums text-destructive">
              {formatUsdc(tx?.amount)}
            </div>
          </div>
          <div className="rounded-lg border border-border bg-card p-3">
            <div className="text-xs text-muted-foreground">Recipient</div>
            <div className="truncate text-sm font-medium text-foreground">
              {tx?.recipient_name ?? shortAddress(tx?.recipient_address)}
            </div>
          </div>
        </div>
        <div className="rounded-lg border border-border bg-card p-3">
          <div className="text-xs text-muted-foreground">Reason</div>
          <p className="mt-1 text-sm text-foreground">{decision?.reason ?? "Policy denied"}</p>
        </div>
        {decision?.checks?.length ? (
          <div className="flex flex-col gap-1">
            {decision.checks.map((c, i) => (
              <div
                key={i}
                className={cn(
                  "flex items-center justify-between rounded-md px-3 py-1.5 text-xs",
                  c.passed ? "bg-background/50 text-muted-foreground" : "bg-destructive/10 text-destructive"
                )}
              >
                <span>{c.name}</span>
                {c.passed ? (
                  <span className="flex items-center gap-1 font-semibold text-success">
                    ok <CheckCircle2 className="h-3 w-3" />
                  </span>
                ) : (
                  <span className="flex items-center gap-1 font-semibold">
                    blocked <XCircle className="h-3 w-3" />
                  </span>
                )}
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function ApprovalRun({
  result,
  deciding,
  onDecide,
}: {
  result: TaskRunResult;
  deciding: boolean;
  onDecide: (action: "approve" | "reject") => void;
}) {
  const tx = result.transaction;
  const decision = result.decision;
  const decided = tx?.status === "executed" || tx?.status === "rejected";

  return (
    <div className="overflow-hidden rounded-xl border border-warning/50 bg-warning/[0.05] animate-fade-up">
      <div className="flex items-center gap-2 bg-warning/10 px-4 py-2.5">
        <Inbox className="h-4 w-4 text-warning" />
        <div className="text-sm font-bold tracking-wide text-warning">
          {decided ? "DECISION RECORDED" : "APPROVAL REQUIRED"}
        </div>
      </div>
      <div className="flex flex-col gap-3 p-4">
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-lg border border-border bg-card p-3">
            <div className="text-xs text-muted-foreground">Requested</div>
            <div className="text-lg font-bold tabular-nums text-foreground">
              {formatUsdc(tx?.amount)}
            </div>
          </div>
          <div className="rounded-lg border border-border bg-card p-3">
            <div className="text-xs text-muted-foreground">Recipient</div>
            <div className="truncate text-sm font-medium text-foreground">
              {tx?.recipient_name ?? shortAddress(tx?.recipient_address)}
            </div>
          </div>
        </div>
        <div className="rounded-lg border border-border bg-card p-3">
          <div className="text-xs text-muted-foreground">Why it paused</div>
          <p className="mt-1 text-sm text-foreground">
            {decision?.reason ?? "This payment exceeds the human approval threshold."}
          </p>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <ShieldCheck className="h-3.5 w-3.5 text-warning" />
          No money moved yet. The human is the final authority — reject to block,
          approve to release the payment.
        </div>
        {!decided && (
          <div className="flex flex-col gap-2 sm:flex-row">
            <Button
              variant="destructive"
              size="sm"
              className="h-9 flex-1"
              disabled={deciding}
              onClick={() => onDecide("reject")}
            >
              {deciding ? <Loader2 className="h-4 w-4 animate-spin" /> : <ThumbsDown className="h-4 w-4" />}
              Reject payment
            </Button>
            <Button
              variant="success"
              size="sm"
              className="h-9 flex-1"
              disabled={deciding}
              onClick={() => onDecide("approve")}
            >
              {deciding ? <Loader2 className="h-4 w-4 animate-spin" /> : <ThumbsUp className="h-4 w-4" />}
              Approve &amp; execute
            </Button>
          </div>
        )}
        {decided && (
          <div
            className={cn(
              "rounded-lg border px-3 py-2.5 text-sm",
              tx?.status === "executed"
                ? "border-success/30 bg-success/10 text-success"
                : "border-destructive/30 bg-destructive/10 text-destructive"
            )}
          >
            {tx?.status === "executed"
              ? `Approved — ${formatUsdc(tx?.amount)} ${tx?.currency ?? "USDC"} executed.`
              : "Rejected — the payment was refused and no money moved."}
          </div>
        )}
      </div>
    </div>
  );
}

function RejectedRun({ result }: { result: TaskRunResult }) {
  const tx = result.transaction;
  return (
    <div className="overflow-hidden rounded-xl border border-destructive/40 bg-destructive/[0.04] animate-fade-up">
      <div className="flex items-center gap-2 bg-destructive/10 px-4 py-2.5">
        <XCircle className="h-4 w-4 text-destructive" />
        <div className="text-sm font-bold tracking-wide text-destructive">PAYMENT REJECTED</div>
      </div>
      <div className="flex flex-col gap-3 p-4">
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-lg border border-border bg-card p-3">
            <div className="text-xs text-muted-foreground">Requested</div>
            <div className="text-lg font-bold tabular-nums text-destructive">
              {formatUsdc(tx?.amount)}
            </div>
          </div>
          <div className="rounded-lg border border-border bg-card p-3">
            <div className="text-xs text-muted-foreground">Recipient</div>
            <div className="truncate text-sm font-medium text-foreground">
              {tx?.recipient_name ?? shortAddress(tx?.recipient_address)}
            </div>
          </div>
        </div>
        <div className="rounded-lg border border-border bg-card p-3">
          <div className="text-xs text-muted-foreground">Reason</div>
          <p className="mt-1 text-sm text-foreground">{tx?.rejection_reason ?? "Rejected by the human."}</p>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <ShieldCheck className="h-3.5 w-3.5 text-success" />
          No money moved — rejected payments never execute.
        </div>
      </div>
    </div>
  );
}

function SuccessRun({ result }: { result: TaskRunResult }) {
  const tx = result.transaction;
  return (
    <div className="overflow-hidden rounded-xl border border-success/40 bg-success/[0.04] animate-fade-up">
      <div className="flex items-center gap-2 bg-success/10 px-4 py-2.5">
        <CheckCircle2 className="h-4 w-4 text-success" />
        <div className="text-sm font-bold tracking-wide text-success">PAYMENT EXECUTED</div>
      </div>
      <div className="flex flex-col gap-3 p-4">
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-lg border border-border bg-card p-3">
            <div className="text-xs text-muted-foreground">Amount</div>
            <div className="text-lg font-bold tabular-nums text-success">
              {formatUsdc(tx?.amount)} {tx?.currency ?? "USDC"}
            </div>
          </div>
          <div className="rounded-lg border border-border bg-card p-3">
            <div className="text-xs text-muted-foreground">Category</div>
            <div className="text-sm font-medium capitalize text-foreground">{tx?.category ?? "—"}</div>
          </div>
        </div>
        <div className="rounded-lg border border-border bg-card p-3">
          <div className="text-xs text-muted-foreground">To</div>
          <div className="truncate text-sm font-medium text-foreground">
            {tx?.recipient_name ?? shortAddress(tx?.recipient_address, 8)}
          </div>
        </div>
        {tx?.tx_hash &&
          (isSimulatedSignature(tx.tx_hash) ? (
            <div className="rounded-lg border border-border bg-card p-3">
              <div className="text-xs text-muted-foreground">Signature</div>
              <div className="mt-1 inline-flex items-center gap-1 font-mono text-xs text-muted-foreground" title="MOCK MODE — simulated transaction, nothing on-chain">
                <ShieldAlert className="h-3 w-3 text-warning" />
                {shortAddress(tx.tx_hash, 10)}
              </div>
            </div>
          ) : (
            <div className="rounded-lg border border-border bg-card p-3">
              <div className="text-xs text-muted-foreground">Signature</div>
              <a
                href={explorerUrlForSignature(tx.tx_hash)}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-1 inline-flex items-center gap-1 font-mono text-xs text-info hover:text-foreground"
              >
                {shortAddress(tx.tx_hash, 10)}
                <ExternalLink className="h-3 w-3" />
              </a>
            </div>
          ))}
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <ShieldCheck className="h-3.5 w-3.5 text-success" />
          All policy checks passed — the payment was submitted through the policy engine.
        </div>
      </div>
    </div>
  );
}

function FailedRun({ result }: { result: TaskRunResult }) {
  return (
    <div className="overflow-hidden rounded-xl border border-destructive/40 bg-destructive/[0.04] animate-fade-up">
      <div className="flex items-center gap-2 bg-destructive/10 px-4 py-2.5">
        <XCircle className="h-4 w-4 text-destructive" />
        <div className="text-sm font-bold tracking-wide text-destructive">EXECUTION FAILED</div>
      </div>
      <div className="p-4">
        <div className="flex items-start gap-2 text-sm text-muted-foreground">
          <Terminal className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
          {result.error}
        </div>
      </div>
    </div>
  );
}