"use client";

import { useRouter } from "next/navigation";
import {
  Wallet,
  Network,
  ShieldCheck,
  Copy,
  Check,
  ExternalLink,
  Server,
  KeyRound,
  Trash2,
  Lock,
  Loader2,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useWalletConnection } from "@/components/wallet/wallet-context";
import { useConfigStatus } from "@/hooks/use-config-status";
import { PageHeader } from "@/components/layout/page-header";
import { Panel } from "@/components/ui/panel";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { api } from "@/lib/api";
import type { LLMKeyStatus } from "@/lib/types";
import { shortAddress } from "@/lib/utils";

function Row({
  icon: Icon,
  label,
  children,
}: {
  icon: React.ElementType;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-4 py-3">
      <div className="flex items-center gap-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-secondary text-muted-foreground">
          <Icon className="h-4 w-4" />
        </div>
        <span className="text-sm text-foreground">{label}</span>
      </div>
      <div className="text-right text-sm">{children}</div>
    </div>
  );
}

function TogglePill({ enabled, label }: { enabled: boolean; label: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded border px-2 py-0.5 text-xs font-medium ${
        enabled
          ? "border-success/30 bg-success/10 text-success"
          : "border-border bg-card text-muted-foreground"
      }`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${enabled ? "bg-success" : "bg-muted-foreground"}`} />
      {label}
    </span>
  );
}

const PROVIDER_META: {
  id: "openai" | "anthropic" | "google";
  label: string;
  placeholder: string;
}[] = [
  {
    id: "openai",
    label: "OpenAI",
    placeholder: "sk-…",
  },
  {
    id: "anthropic",
    label: "Anthropic",
    placeholder: "sk-ant-…",
  },
  {
    id: "google",
    label: "Google AI",
    placeholder: "AIza…",
  },
];

function SourcePill({ status }: { status: LLMKeyStatus }) {
  if (status.source === "user") {
    return <TogglePill enabled label="Your key" />;
  }
  if (status.source === "server") {
    return <TogglePill enabled label="Server default" />;
  }
  return <TogglePill enabled={false} label="Mock fallback" />;
}

function LLMKeyManager({ wallet }: { wallet: string }) {
  const [keys, setKeys] = useState<LLMKeyStatus[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setError(null);
      setKeys(await api.listLlmKeys(wallet));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load provider keys");
      setKeys([]);
    }
  }, [wallet]);

  useEffect(() => {
    void load();
  }, [load]);

  const save = async (provider: string, apiKey: string) => {
    if (!apiKey.trim()) return;
    setSaving(provider);
    try {
      await api.setLlmKey(wallet, provider, apiKey.trim());
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save key");
    } finally {
      setSaving(null);
    }
  };

  const remove = async (provider: string) => {
    setSaving(provider);
    try {
      await api.deleteLlmKey(wallet, provider);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to remove key");
    } finally {
      setSaving(null);
    }
  };

  if (keys === null) return <Spinner label="Loading provider keys…" />;

  return (
    <div className="flex flex-col gap-3">
      {error ? (
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">
          {error}
        </div>
      ) : null}

      {PROVIDER_META.map((meta) => {
        const status = keys.find((k) => k.provider === meta.id) ?? {
          provider: meta.id,
          has_key: false,
          source: "mock" as const,
        };
        return <ProviderRow key={meta.id} meta={meta} status={status} saving={saving} onSave={save} onRemove={remove} />;
      })}

      <p className="flex items-start gap-2 text-xs text-muted-foreground">
        <Lock className="mt-0.5 h-3.5 w-3.5 shrink-0" />
        Keys are encrypted at rest (per wallet) and only reach the matching provider during a
        task run. Without a key, agents use the server default, or the deterministic mock so the
        demo always works.
      </p>
    </div>
  );
}

function ProviderRow({
  meta,
  status,
  saving,
  onSave,
  onRemove,
}: {
  meta: { id: "openai" | "anthropic" | "google"; label: string; placeholder: string };
  status: LLMKeyStatus;
  saving: string | null;
  onSave: (provider: string, apiKey: string) => Promise<void>;
  onRemove: (provider: string) => Promise<void>;
}) {
  const [value, setValue] = useState("");
  const busy = saving === meta.id;

  return (
    <div className="rounded-lg border border-border bg-background/40 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-secondary text-muted-foreground">
            <KeyRound className="h-4 w-4" />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-foreground">{meta.label}</span>
            <SourcePill status={status} />
          </div>
        </div>
        {status.has_key ? (
          <Button
            variant="ghost"
            size="sm"
            disabled={busy}
            onClick={() => void onRemove(meta.id)}
            className="text-muted-foreground hover:text-destructive"
          >
            {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
            <span className="ml-1">Remove</span>
          </Button>
        ) : null}
      </div>
      <div className="mt-3 flex flex-col gap-2 sm:flex-row">
        <Input
          type="password"
          placeholder={meta.placeholder}
          value={value}
          disabled={busy}
          autoComplete="off"
          onChange={(e) => setValue(e.target.value)}
          className="font-mono"
        />
        <Button
          size="sm"
          disabled={!value.trim() || busy}
          onClick={() => void onSave(meta.id, value)}
        >
          {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Save key"}
        </Button>
      </div>
    </div>
  );
}

export function SettingsPage() {
  const router = useRouter();
  const { address, isDemo, connected, disconnect, openWalletSelect } = useWalletConnection();
  const { status } = useConfigStatus();
  const [copied, setCopied] = useState(false);

  const copy = () => {
    if (!address) return;
    navigator.clipboard?.writeText(address);
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Settings"
        description="Wallet, network and provider configuration. Your own LLM API keys are encrypted at rest and never exposed to the browser."
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Wallet */}
        <Panel title="Connected wallet" description="The wallet that funds your agents">
          {!connected ? (
            <div className="flex flex-col items-start gap-3 py-2">
              <p className="text-sm text-muted-foreground">No wallet connected.</p>
              <Button onClick={() => openWalletSelect()}>Connect wallet</Button>
            </div>
          ) : (
            <>
              <Row icon={Wallet} label="Address">
                <button
                  onClick={copy}
                  className="inline-flex items-center gap-1.5 font-mono text-xs text-foreground transition-colors hover:text-primary"
                  title={address ?? undefined}
                >
                  {shortAddress(address, 8)}
                  {copied ? (
                    <Check className="h-3.5 w-3.5 text-success" />
                  ) : (
                    <Copy className="h-3.5 w-3.5 text-muted-foreground" />
                  )}
                </button>
              </Row>
              <Row icon={ShieldCheck} label="Signing">
                {isDemo ? (
                  <TogglePill enabled={false} label="Simulated wallet" />
                ) : (
                  <TogglePill enabled label="Phantom / Solana wallet" />
                )}
              </Row>
              <div className="flex justify-end pt-2">
                <Button variant="outline" size="sm" onClick={disconnect}>
                  Disconnect
                </Button>
              </div>
            </>
          )}
        </Panel>

        {/* Network */}
        <Panel title="Network" description="Where settlement happens">
          <Row icon={Network} label="Blockchain">
            <div className="flex items-center justify-end gap-2">
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  status?.payment_mode === "mock" ? "bg-warning" : "bg-success"
                }`}
              />
              <span className="text-foreground">
                {status?.payment_mode === "mock" ? "Solana Demo" : "Solana Devnet"}
              </span>
            </div>
          </Row>
          <Row icon={Server} label="Payment mode">
            {status?.payment_mode === "mock" ? (
              <TogglePill enabled={false} label="MOCK" />
            ) : (
              <TogglePill enabled label="REAL" />
            )}
          </Row>
          <Row icon={Network} label="USDC">
            <span className="text-muted-foreground">SPL USDC</span>
          </Row>
          <div className="pt-2">
            <a
              href="https://explorer.solana.com/?cluster=devnet"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs font-medium text-info hover:text-foreground"
            >
              View Solana Devnet explorer <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </Panel>

        {/* AI providers — bring-your-own key */}
        <div className="lg:col-span-2">
          <Panel
            title="AI providers — bring your own key"
            description="Attach your own OpenAI, Anthropic or Google key. Agents run through the model you configure; keys are encrypted at rest and never leave the server."
          >
            {!connected || !address ? (
              <div className="flex flex-col items-start gap-3 py-2">
                <p className="text-sm text-muted-foreground">
                  Connect a wallet to manage provider keys for it.
                </p>
<Button onClick={() => openWalletSelect()}>Connect wallet</Button>
              </div>
            ) : (
              <LLMKeyManager wallet={address} />
            )}
          </Panel>
        </div>

        {/* Backend */}
        <Panel title="Backend" description="Runtime configuration reported by the API">
          <Row icon={Server} label="API">
            <span className="text-muted-foreground">FastAPI · /api/v1</span>
          </Row>
          <Row icon={Network} label="Solana SDK">
            {status?.solana_configured ? (
              <TogglePill enabled label="Configured" />
            ) : (
              <TogglePill enabled={false} label="Blank RPC" />
            )}
          </Row>
          <Row icon={Server} label="Redis">
            {status?.redis_configured ? (
              <TogglePill enabled label="In-memory fallback" />
            ) : (
              <TogglePill enabled={false} label="Caching off" />
            )}
          </Row>
          {status?.missing_config.length ? (
            <div className="mt-2">
              <div className="mb-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                Advisory — unset configuration
              </div>
              <div className="flex flex-wrap gap-1.5">
                {status.missing_config.map((m) => (
                  <span
                    key={m}
                    className="rounded border border-border bg-card px-2 py-0.5 font-mono text-[10px] text-muted-foreground"
                  >
                    {m}
                  </span>
                ))}
              </div>
            </div>
          ) : null}
        </Panel>
      </div>

      {/* Security note */}
      <Panel title="Security model" description="Why agents can't just do whatever they want">
        <div className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-3">
          <div className="rounded-lg border border-border bg-background/40 p-3">
            <div className="font-medium text-foreground">Keys stay server-side</div>
            <p className="mt-1 text-xs text-muted-foreground">
              The AI can never supply private keys, raw signed transactions, or arbitrary
              program invocations. The backend builds validated requests.
            </p>
          </div>
          <div className="rounded-lg border border-border bg-background/40 p-3">
            <div className="font-medium text-foreground">LLM output is untrusted</div>
            <p className="mt-1 text-xs text-muted-foreground">
              Amounts, recipients, and permissions are enforced deterministically by the
              policy engine — never by the model.
            </p>
          </div>
          <div className="rounded-lg border border-border bg-background/40 p-3">
            <div className="font-medium text-foreground">Humans are final authority</div>
            <p className="mt-1 text-xs text-muted-foreground">
              High-value requests pause for approval and expire. Pause or kill any agent
              from its profile at any time.
            </p>
          </div>
        </div>
        <div className="mt-3 flex justify-end">
          <Button variant="ghost" size="sm" onClick={() => router.push("/agents")}>
            Review your agents
          </Button>
        </div>
      </Panel>
    </div>
  );
}