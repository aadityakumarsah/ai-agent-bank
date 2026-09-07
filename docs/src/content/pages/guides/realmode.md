# Go live on devnet

"Real mode" is an explicit opt-in that points the same engine at real Solana
devnet USDC. This guide is the checklist for switching with clean hands.

## The env switch (backend)

```env
# backend/.env
USE_REAL_PAYMENT=true
SOLANA_RPC_URL=https://api.devnet.solana.com          # or Helius devnet URL
SOLANA_PRIVATE_KEY=…base58 master keypair…            # derives every escrow
# optional
# SOLANA_USDC_MINT=4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU   # devnet default
```

- With `USE_REAL_PAYMENT` absent/false, or `SOLANA_RPC_URL` blank, all payments
  are **mock**.
- Leaving `DEMO_MODE=true` is fine for a devnet sandbox, but remember the
  one-click demos now produce **real devnet signatures** where they execute.
  Disable it for clean behaviour (or before any kind of "showcase").

## The frontend switch

```env
# frontend/.env.local
NEXT_PUBLIC_SOLANA_NETWORK=devnet
NEXT_PUBLIC_SOLANA_RPC_URL=https://api.devnet.solana.com
NEXT_PUBLIC_SOLANA_USDC_MINT=4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU
```

Keep the mint and network in sync with the backend — a mismatch signs tokens the
backend never requested.

## Wallet setup

1. Create a **devnet** Phantom/Backpack wallet (or devnet network in the app).
2. Top it up: <https://faucet.solana.com> for devnet SOL; the configurable USDC
   mint defaults to devnet.
3. Connect it in the dashboard.

## Verify with a guided sequence

1. `POST /users` with your wallet → 200.
2. Create an agent, set a policy, and check `GET /transactions` shows blank.
3. `POST /agents/{id}/fund {"amount": 100}` → you get a **real payment request**
   (network, mint, `to_address` = escrow).
4. Sign in your wallet, `POST /fund/confirm` → funded with a real signature.
5. Run a task that stays under `require_approval_above` → `mode: "solana"`,
   `simulated: false`, real `tx_hash`, open it in
   `https://explorer.solana.com/tx/…?cluster=devnet`.
6. Watch a cap or a bad recipient get **blocked** the same way mock does.

## Cheap ways to truncate scope

- Keep **caps small** (demo bots' `20/100/1000` style). Nothing on a devnet
  escrow is actually risky — the discipline you're rehearsing here is the exact
  posture for mainnet.
- If you only want to see one real transfer, run just the funding flow and keep
  the rest mock.

> [!WARNING]
> There is **no simulated token half-way**. If `USE_REAL_PAYMENT=true`, every
> executed payment is a devnet transaction; if you later flip it off, new
> payments are mock again — but already-executed transactions stay real and
> on-chain. The labels on each result (`mode`, `simulated`) are the only honest
> way to tell them apart afterwards.

Related: [USDC on Solana](/payments/usdc) · [Production deployment](/advanced/production).