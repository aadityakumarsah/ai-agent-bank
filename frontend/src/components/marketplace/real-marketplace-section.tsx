"use client";
import { useState, useEffect, useCallback } from "react";
import {
  Store,
  Plus,
  Loader2,
  CheckCircle2,
  XCircle,
  ShoppingCart,
  Clock,
  AlertTriangle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Panel } from "@/components/ui/panel";
import { Badge } from "@/components/ui/badge";
import { Dialog } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { formatUsdc, shortAddress } from "@/lib/utils";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api";
import type {
  ProviderProfile,
  ServiceListing,
  QuoteOut,
  PurchaseSubmitResult,
  PurchaseOut,
  Agent,
} from "@/lib/types";

export function RealMarketplaceSection({ address }: { address: string | null }) {
  const { toast } = useToast();
  const [providers, setProviders] = useState<ProviderProfile[]>([]);
  const [listings, setListings] = useState<ServiceListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [registerOpen, setRegisterOpen] = useState(false);
  const [purchaseListing, setPurchaseListing] = useState<ServiceListing | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [p, l] = await Promise.all([api.listProviders(), api.listListings()]);
      setProviders(p);
      setListings(l);
    } catch (e) {
      toast({
        type: "error",
        title: "Failed to load marketplace",
        description: e instanceof Error ? e.message : "Unknown error",
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) return <Spinner label="Loading marketplace..." />;

  return (
    <div className="flex flex-col gap-6">
      {providers.length === 0 && listings.length === 0 ? (
        <EmptyState
          icon={Store}
          title="No providers configured yet"
          description="Register a provider to start offering services on the marketplace."
          actionLabel="Register Provider"
          onAction={() => setRegisterOpen(true)}
        />
      ) : (
        <>
          <div className="flex justify-end">
            <Button size="sm" onClick={() => setRegisterOpen(true)}>
              <Plus className="h-4 w-4" />
              Register Provider
            </Button>
          </div>
          {listings.length > 0 && (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {listings.map((listing) => (
                <ListingCard
                  key={listing.id}
                  listing={listing}
                  address={address}
                  onBuy={() => setPurchaseListing(listing)}
                />
              ))}
            </div>
          )}
          {listings.length === 0 && providers.length > 0 && (
            <EmptyState
              icon={Store}
              title="No active listings"
              description="Providers are registered but have no active service listings yet."
            />
          )}
        </>
      )}

      {providers.length > 0 && (
        <Panel title="Registered Providers" description="All registered provider integrations">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {providers.map((p) => (
              <div
                key={p.id}
                className="flex items-start gap-3 rounded-lg border border-border bg-background/40 p-3"
              >
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-secondary text-muted-foreground">
                  <Store className="h-4 w-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="text-sm font-semibold text-foreground">{p.name}</span>
                    {p.verified ? (
                      <Badge variant="success">Verified</Badge>
                    ) : (
                      <Badge variant="warning">Pending</Badge>
                    )}
                  </div>
                  <div className="mt-0.5 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                    <span className="font-mono">{p.adapter}</span>
                    <span>·</span>
                    <span>{p.category}</span>
                    <span>·</span>
                    <span className="font-mono">{shortAddress(p.wallet_address, 6)}</span>
                  </div>
                  {p.supports.length > 0 && (
                    <div className="mt-1.5 flex flex-wrap gap-1">
                      {p.supports.map((s) => (
                        <span
                          key={s}
                          className="rounded border border-border bg-card px-1.5 py-px text-[10px] font-medium text-muted-foreground"
                        >
                          {s}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Panel>
      )}

      {registerOpen && (
        <RegisterProviderDialog
          address={address}
          onClose={() => setRegisterOpen(false)}
          onRegistered={() => {
            setRegisterOpen(false);
            void load();
          }}
        />
      )}

      {purchaseListing && address && (
        <PurchaseDialog
          listing={purchaseListing}
          address={address}
          onClose={() => setPurchaseListing(null)}
          onCompleted={() => {
            setPurchaseListing(null);
          }}
        />
      )}
    </div>
  );
}

function ListingCard({
  listing,
  address,
  onBuy,
}: {
  listing: ServiceListing;
  address: string | null;
  onBuy: () => void;
}) {
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4 transition-colors hover:border-primary/30">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-foreground">{listing.name}</h3>
          <p className="mt-0.5 text-xs text-muted-foreground">{listing.provider_name}</p>
        </div>
        <Badge variant={listing.status === "active" ? "success" : "neutral"}>
          {listing.status}
        </Badge>
      </div>
      {listing.description && (
        <p className="text-xs leading-relaxed text-muted-foreground line-clamp-2">
          {listing.description}
        </p>
      )}
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="font-semibold tabular-nums text-foreground">
          {formatUsdc(listing.price)}
        </span>
        <span className="text-muted-foreground">{listing.currency}</span>
        <span className="rounded border border-border bg-card px-1.5 py-px text-[10px] font-medium uppercase text-muted-foreground">
          {listing.category}
        </span>
      </div>
      <div className="mt-auto flex justify-end border-t border-border pt-3">
        <Button size="sm" disabled={!address} onClick={onBuy}>
          <ShoppingCart className="h-3.5 w-3.5" />
          Buy
        </Button>
      </div>
    </div>
  );
}

function RegisterProviderDialog({
  address,
  onClose,
  onRegistered,
}: {
  address: string | null;
  onClose: () => void;
  onRegistered: () => void;
}) {
  const { toast } = useToast();
  const [name, setName] = useState("");
  const [apiBaseUrl, setApiBaseUrl] = useState("https://api.mymemory.translated.net");
  const [walletAddress, setWalletAddress] = useState("");
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState<ProviderProfile | null>(null);

  const submit = async () => {
    if (!name.trim() || !walletAddress.trim()) return;
    setPending(true);
    try {
      const res = await api.registerProvider({
        name: name.trim(),
        adapter: "mymemory",
        api_base_url: apiBaseUrl.trim(),
        category: "api",
        wallet_address: walletAddress.trim(),
        supports: ["translate"],
        description: "Public translation API integration",
        owner_wallet: address ?? undefined,
      });
      setResult(res);
      toast({
        type: res.verified ? "success" : "warning",
        title: res.verified ? "Provider registered" : "Provider registered (pending verification)",
        description: res.verified
          ? "The provider passed the health check and is active."
          : "The health check failed; the provider is in pending status.",
      });
      onRegistered();
    } catch (e) {
      toast({
        type: "error",
        title: "Registration failed",
        description: e instanceof Error ? e.message : "Unknown error",
      });
    } finally {
      setPending(false);
    }
  };

  return (
    <Dialog
      open
      onClose={onClose}
      title="Register Provider"
      description="Register a new provider integration for the marketplace."
      footer={
        <>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} disabled={pending || !name.trim() || !walletAddress.trim()}>
            {pending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            Register
          </Button>
        </>
      }
    >
      {result ? (
        <div className="flex flex-col items-center gap-3 py-4 text-center">
          {result.verified ? (
            <CheckCircle2 className="h-10 w-10 text-success" />
          ) : (
            <AlertTriangle className="h-10 w-10 text-warning" />
          )}
          <div>
            <div className="text-sm font-semibold text-foreground">{result.name}</div>
            <div className="mt-0.5 text-xs text-muted-foreground">
              {result.verified
                ? "Verified and active."
                : "Pending — the health check failed. The provider is registered but not yet verified."}
            </div>
          </div>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          <Input
            id="provider-name"
            label="Provider name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. MyMemory Translation"
          />
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-muted-foreground">Adapter</label>
            <select
              value="mymemory"
              disabled
              className="flex h-10 w-full rounded-md border border-input bg-card px-3 py-2 text-sm text-foreground"
            >
              <option value="mymemory">MyMemory (public translation API)</option>
            </select>
          </div>
          <Input
            id="api-base-url"
            label="API base URL"
            value={apiBaseUrl}
            onChange={(e) => setApiBaseUrl(e.target.value)}
          />
          <Input
            id="wallet-address"
            label="Provider wallet address (devnet USDC, base58)"
            value={walletAddress}
            onChange={(e) => setWalletAddress(e.target.value)}
            placeholder="Base58 Solana address"
          />
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-muted-foreground">Capabilities</label>
            <div className="flex items-center gap-2">
              <input type="checkbox" checked disabled className="h-4 w-4" />
              <span className="text-sm text-foreground">translate</span>
            </div>
          </div>
          <p className="text-xs text-muted-foreground">
            Settlement goes to the provider's devnet wallet through the policy
            engine. MyMemory itself is a public API and quotes are the Agent
            Bank's own pricing.
          </p>
        </div>
      )}
    </Dialog>
  );
}

function PurchaseDialog({
  listing,
  address,
  onClose,
  onCompleted,
}: {
  listing: ServiceListing;
  address: string;
  onClose: () => void;
  onCompleted: () => void;
}) {
  const { toast } = useToast();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<number | null>(null);
  const [text, setText] = useState("");
  const [langpair, setLangpair] = useState("en|es");
  const [quote, setQuote] = useState<QuoteOut | null>(null);
  const [submitResult, setSubmitResult] = useState<PurchaseSubmitResult | null>(null);
  const [purchases, setPurchases] = useState<PurchaseOut[]>([]);
  const [step, setStep] = useState<"form" | "quote" | "result">("form");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listAgents(address).then(setAgents).catch(() => {});
  }, [address]);

  const loadPurchases = useCallback(async () => {
    if (selectedAgentId) {
      try {
        const p = await api.listPurchasesByAgent(selectedAgentId);
        setPurchases(p);
      } catch {
        /* ignore */
      }
    }
  }, [selectedAgentId]);

  useEffect(() => {
    void loadPurchases();
  }, [loadPurchases]);

  const selectedAgent = agents.find((a) => a.id === selectedAgentId);

  const getQuote = async () => {
    if (!selectedAgentId) return;
    setLoading(true);
    setError(null);
    try {
      const q = await api.quoteListing(listing.id, selectedAgentId, { text, langpair });
      setQuote(q);
      setStep("quote");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Quote failed");
    } finally {
      setLoading(false);
    }
  };

  const confirmPurchase = async () => {
    if (!quote) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.submitPurchase(quote.intent_id);
      setSubmitResult(res);
      setStep("result");
      if (res.outcome === "completed") {
        toast({
          type: "success",
          title: "Purchase completed",
          description: `${formatUsdc(quote.amount)} ${quote.currency} paid to ${quote.provider_name}.`,
        });
      } else if (res.outcome === "approval_required") {
        toast({
          type: "info",
          title: "Approval required",
          description: "The payment is paused pending human approval.",
        });
      } else if (res.outcome === "blocked") {
        toast({
          type: "error",
          title: "Payment blocked",
          description: res.reason ?? "The policy engine denied this payment.",
        });
      } else {
        toast({
          type: "error",
          title: "Purchase failed",
          description: res.reason ?? "The purchase could not be completed.",
        });
      }
      void loadPurchases();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Purchase failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog
      open
      onClose={onClose}
      title={`Buy: ${listing.name}`}
      description={`From ${listing.provider_name} — ${formatUsdc(listing.price)} ${listing.currency}`}
      size="lg"
    >
      {step === "form" && (
        <div className="flex flex-col gap-4">
          {error && (
            <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2.5 text-sm text-destructive">
              {error}
            </div>
          )}

          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-muted-foreground">Select agent</label>
            <select
              value={selectedAgentId ?? ""}
              onChange={(e) => setSelectedAgentId(Number(e.target.value) || null)}
              className="flex h-10 w-full rounded-md border border-input bg-card px-3 py-2 text-sm text-foreground"
            >
              <option value="">Choose an agent...</option>
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name} — balance {formatUsdc(a.balance)}
                </option>
              ))}
            </select>
          </div>

          {selectedAgent && (
            <div className="rounded-lg border border-border bg-background/40 px-3 py-2">
              <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                Agent escrow balance
              </div>
              <div className="text-lg font-bold tabular-nums text-foreground">
                {formatUsdc(selectedAgent.balance)} USDC
              </div>
            </div>
          )}

          <Textarea
            id="payload-text"
            label="Text to translate"
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={3}
            placeholder="Enter text to translate..."
          />

          <Input
            id="langpair"
            label="Language pair (source|target)"
            value={langpair}
            onChange={(e) => setLangpair(e.target.value)}
            placeholder="en|es"
          />

          <div className="rounded-lg border border-border bg-background/40 px-3 py-2">
            <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
              Price
            </div>
            <div className="text-lg font-bold tabular-nums text-foreground">
              {formatUsdc(listing.price)} {listing.currency}
            </div>
          </div>

          <div className="flex justify-end gap-2 border-t border-border pt-4">
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button onClick={getQuote} disabled={loading || !selectedAgentId || !text.trim()}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Get Quote
            </Button>
          </div>
        </div>
      )}

      {step === "quote" && quote && (
        <div className="flex flex-col gap-4">
          {error && (
            <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2.5 text-sm text-destructive">
              {error}
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg border border-border bg-card p-3">
              <div className="text-xs text-muted-foreground">Amount</div>
              <div className="text-lg font-bold tabular-nums text-foreground">
                {formatUsdc(quote.amount)} {quote.currency}
              </div>
            </div>
            <div className="rounded-lg border border-border bg-card p-3">
              <div className="text-xs text-muted-foreground">Provider</div>
              <div className="text-sm font-medium text-foreground">{quote.provider_name}</div>
            </div>
          </div>

          {quote.notes.length > 0 && (
            <div className="rounded-lg border border-border bg-background/40 px-3 py-2">
              <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                Notes
              </div>
              <ul className="mt-1 list-disc pl-4 text-xs text-muted-foreground">
                {quote.notes.map((n, i) => (
                  <li key={i}>{n}</li>
                ))}
              </ul>
            </div>
          )}

          <p className="text-xs text-muted-foreground">
            Settlement goes to the provider's devnet wallet through the policy
            engine; MyMemory itself is a public API and quotes are the Agent
            Bank's own pricing.
          </p>

          <div className="flex justify-end gap-2 border-t border-border pt-4">
            <Button variant="outline" onClick={() => setStep("form")}>
              Back
            </Button>
            <Button onClick={confirmPurchase} disabled={loading}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
              Confirm purchase
            </Button>
          </div>
        </div>
      )}

      {step === "result" && submitResult && (
        <div className="flex flex-col gap-4">
          {submitResult.outcome === "completed" && (
            <div className="overflow-hidden rounded-xl border border-success/40 bg-success/[0.04]">
              <div className="flex items-center gap-2 bg-success/10 px-4 py-2.5">
                <CheckCircle2 className="h-4 w-4 text-success" />
                <div className="text-sm font-bold tracking-wide text-success">PURCHASE COMPLETED</div>
              </div>
              <div className="p-4">
                <p className="text-sm text-foreground">
                  Paid {quote && formatUsdc(quote.amount)} to {quote?.provider_name} for &apos;{listing.name}&apos;.
                </p>
                {submitResult.transaction?.tx_hash && (
                  <p className="mt-1 text-xs text-muted-foreground font-mono">
                    tx: {submitResult.transaction.tx_hash}
                  </p>
                )}
              </div>
            </div>
          )}

          {submitResult.outcome === "approval_required" && (
            <div className="overflow-hidden rounded-xl border border-warning/50 bg-warning/[0.05]">
              <div className="flex items-center gap-2 bg-warning/10 px-4 py-2.5">
                <Clock className="h-4 w-4 text-warning" />
                <div className="text-sm font-bold tracking-wide text-warning">APPROVAL REQUIRED</div>
              </div>
              <div className="p-4">
                <p className="text-sm text-foreground">
                  The payment is paused — approve or reject it in{' '}
                  <a href="/approvals" className="font-semibold text-primary hover:underline">
                    Approvals
                  </a>
                  .
                </p>
              </div>
            </div>
          )}

          {submitResult.outcome === "blocked" && (
            <div className="overflow-hidden rounded-xl border border-destructive/40 bg-destructive/[0.04]">
              <div className="flex items-center gap-2 bg-destructive/10 px-4 py-2.5">
                <XCircle className="h-4 w-4 text-destructive" />
                <div className="text-sm font-bold tracking-wide text-destructive">BLOCKED</div>
              </div>
              <div className="p-4">
                <p className="text-sm text-foreground">
                  {submitResult.reason ?? "The policy engine denied this payment."}
                </p>
              </div>
            </div>
          )}

          {submitResult.outcome === "failed" && (
            <div className="overflow-hidden rounded-xl border border-destructive/40 bg-destructive/[0.04]">
              <div className="flex items-center gap-2 bg-destructive/10 px-4 py-2.5">
                <XCircle className="h-4 w-4 text-destructive" />
                <div className="text-sm font-bold tracking-wide text-destructive">FAILED</div>
              </div>
              <div className="p-4">
                <p className="text-sm text-foreground">
                  {submitResult.reason ?? "The purchase could not be completed."}
                </p>
              </div>
            </div>
          )}

          <div className="flex justify-end border-t border-border pt-4">
            <Button onClick={onClose}>Done</Button>
          </div>
        </div>
      )}
    </Dialog>
  );
}
