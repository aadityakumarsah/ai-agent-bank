# USDC on Solana

Payments are SPL-token **USDC** transfers on **Solana**. The token and network
are configurable but default to the devnet USDC mint.

## Mint addresses

| Network | USDC mint |
|---|---|
| Devnet (default) | `4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU` |
| Mainnet-beta | `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v` |

- USDC uses **6 decimals** (`USDC_DECIMALS = 6`) — the ledger stores amounts as
  `Numeric(20,6)`.
- `SOLANA_USDC_MINT` can override the default; if unset it is chosen from the
  network: devnet → devnet mint, mainnet-beta → mainnet mint.

## The transfer

`SolanaPaymentService.execute_payment` builds, signs, and submits a **SPL Token
Program `TransferChecked`** instruction with the expected decimals checked
against the mint, waits for confirmation, and can re-verify a signature.

Under the hood:

1. Resolve the recipient's associated token account (`get_associated_token_address`)
   or create it (ATA) as needed.
2. Build a `Transaction` with the `TransferChecked` instruction and a base fee
   (estimated via the RPC; devnet base is typically 5,000 lamports).
3. Sign with the backend's derived escrow keypair for the source account.
4. `send_raw_transaction` the serialized transaction and wait for confirmation.
5. Return a proof: `tx_hash`, `mode`, `simulated`, and an `explorer_url`.

```json
{
  "tx_hash": "2mX1…",
  "mode": "solana",
  "simulated": false,
  "explorer_url": "https://explorer.solana.com/tx/2mX1…?cluster=devnet",
  "network": "devnet",
  "mint": "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU"
}
```

> [!WARNING]
> The frontend's browser helpers use the **same devnet mint** by default.
> `NEXT_PUBLIC_SOLANA_NETWORK`/`NEXT_PUBLIC_SOLANA_USDC_MINT`/`NEXT_PUBLIC_SOLANA_RPC_URL`
> must be kept consistent with the backend if you customise them — mixing a
> devnet backend with a mainnet wallet build signs real tokens.

## RPC

The backend calls `SOLANA_RPC_URL` (devnet Helius or any public devnet RPC). A
blank value forces **mock mode**. The frontend uses
`NEXT_PUBLIC_SOLANA_RPC_URL` for wallet balance/ATA lookups and to let the user's
wallet build/sign the funding transfer.

## Security posture

- The backend never accepts instructions, program IDs, or serialized transactions
  from clients — only validated amounts and base58 addresses.
- Signing happens server-side with the escrow keypair derived from
  `SOLANA_PRIVATE_KEY`. See [Private keys](/security/keys).

Next: [Funding & payment requests](/payments/funding).