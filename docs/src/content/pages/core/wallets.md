# Agent wallets & escrow

Agents never hold a private key you have to babysit. Each agent is associated
with a server-side **escrow account**: a public address derived deterministically
from the backend's master keypair plus the agent's owner and id.

## The escrow address

- It is generated when the agent is created by
  `payment_service._derive_escrow_keypair` and exposed as
  `Agent.escrow_address`.
- It is the **funding target** (you send USDC to it) and the **payment source**
  (outgoing transfers are signed from it).
- The derived secret key material lives only in backend memory, derived from
  `SOLANA_PRIVATE_KEY` on demand. It is never stored, never returned by the API,
  and never exposed to the LLM or the frontend.

## Balances

The agent's `balance` and `total_spent` are decimals stored server-side (the
ledger). USDC uses 6 decimal places, so the schema stores them as `Numeric(20,6)`.

- Executed payments subtract from `balance` and add to `total_spent`.
- Blocked or rejected payments move nothing.
- **Mock mode**: funding credits the ledger directly with a `mock_` transaction;
  the blockchain is never touched.
- **Real mode**: your wallet signs a real transfer into the agent's escrow — see
  [Funding & payment requests](/payments/funding).

## Why escrow?

Separating a funded **escrow** from the signer means:

1. The AI never controls the key material used to sign.
2. You fund a *specific amount* and define *what it may buy* in one place.
3. Every payment out of the escrow is policy-gated and audited — there is no
   "wallet key" the agent could move funds with unobserved.

## Withdrawals

`blocked_withdrawals` is **on by default** in every policy: an agent cannot
drain its escrow back into a human wallet. There is no withdrawal endpoint.

> [!WARNING]
> The escrow is derived from the master key. Losing `SOLANA_PRIVATE_KEY` means
> losing the ability to derive (and hence move) every agent's escrow funds.

Related: [Funding & payment requests](/payments/funding) and
[Private keys & secrets](/security/keys).