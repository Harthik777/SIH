# Audit ledger and Bitcoin timestamp decision

**Decision:** retain Sentinel's local append-only SHA-256 action chain and add an optional, privacy-preserving external checkpoint through OpenTimestamps and Bitcoin. Do not store evidence on a blockchain and do not run a blockchain node merely for product branding.

## Why this hybrid design is justified

The local audit chain records sequence, UTC time, actor, action, target, previous hash and content hash. `/api/audit/verify` recomputes the chain and detects modified content or broken linkage. This remains fast, inspectable, free, and available without internet access.

A host administrator could still replace the entire local chain and recompute it. A timestamp published through a separately administered OpenTimestamps calendar creates the missing external witness: after Bitcoin aggregation, a saved proof can show that a specific Sentinel checkpoint existed no later than the attesting block.

This does **not** make the application database immutable. It makes silent rewriting of history after an externally witnessed checkpoint detectable when the saved checkpoint, `.ots` proof and current chain are compared.

## Privacy boundary

Sentinel creates a checkpoint document containing only:

- audit method and entry count;
- the SHA-256 audit-chain head; and
- checkpoint creation time.

OpenTimestamps hashes that document, appends a fresh random nonce, hashes it again, and submits only the resulting opaque 32-byte commitment. FIR text, graph content, names, phone numbers, victim information, account data, evidence identifiers and audit-event content never leave Sentinel and never enter Bitcoin.

## Honest proof states

The interface deliberately separates these states:

1. `prepared` — local checkpoint only; no external timestamp claim.
2. `calendar-pending` — one or more calendars accepted the blinded commitment; not yet Bitcoin-confirmed.
3. `bitcoin-attested` — the upgraded proof contains a Bitcoin block attestation, but external block-header verification has not completed.
4. `bitcoin-confirmed` — the proof's Merkle-root commitment matches a Bitcoin header obtained through the configured Esplora endpoint.

For maximum trust minimization, export the checkpoint and `.ots` proof and verify them with an independently operated Bitcoin Core node. The hosted verifier uses a public Bitcoin-header service and therefore inherits availability and best-chain trust from that service.

## Operational controls

- Online anchoring is configuration-gated with `SENTINEL_CONNECTIVITY_MODE=hybrid` and `SENTINEL_AUDIT_ANCHOR_MODE=opentimestamps`.
- The public synthetic showcase permits at most three submission attempts per service instance to prevent calendar abuse.
- Private deployments require a supervisor-authorized session for checkpoint submission and refresh.
- Calendar URLs are configured server-side; proof upgrades accept only HTTPS OpenTimestamps calendar domains.
- A failed or unavailable external service never blocks local analysis, audit verification, reporting, or export.
- Public free-hosting storage is ephemeral, so users must download both the checkpoint JSON and `.ots` proof for durable custody.

## API and evidence

- `GET /api/audit/anchors` — capability, privacy boundary and checkpoint states.
- `POST /api/audit/anchors` with `{ "submit": false }` — prepare locally.
- `POST /api/audit/anchors` with `{ "submit": true }` — prepare and submit a blinded commitment.
- `POST /api/audit/anchors/{id}/refresh` — request a proof upgrade and verify an available Bitcoin attestation.
- `GET /api/audit/anchors/{id}/checkpoint` — download the checkpoint document.
- `GET /api/audit/anchors/{id}/proof` — download the standard `.ots` proof.
- `GET /api/audit/anchors/{id}/bundle` — download the checkpoint, proof and verification note together.

The upstream OpenTimestamps client documents that calendar receipts are initially incomplete and Bitcoin aggregation can take hours. Sentinel therefore never labels initial calendar acceptance as on-chain confirmation.

## SIH claim boundary

Sentinel now implements a real Bitcoin-backed timestamp path for audit-chain checkpoints. The defensible claim is **privacy-preserving external audit witnessing**, not “all evidence is stored on blockchain,” not instant finality, and not agency-grade immutable custody. This limited use adds a genuine independent trust boundary while preserving the offline-capable investigative workflow.
