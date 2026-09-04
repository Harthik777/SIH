# Audit ledger architecture decision

**Decision:** use a local append-only SHA-256 action chain; do not add a blockchain to the current Sentinel deployment.

## Why this is the correct current design

Sentinel's competition and private-pilot profiles have one accountable administrative authority, must run offline, and must remain free on a single machine. Consensus among mutually distrustful writers—the main reason to use a blockchain—does not exist in this threat model. Adding a blockchain node would increase storage, deployment, key-management and recovery complexity without preventing an administrator who controls the only host from rewriting both application data and the local ledger.

The existing chain gives every event a sequence, timestamp, actor, action, target, previous hash and content hash. `/api/audit/verify` recomputes the chain and detects edits, deletions, insertion and broken linkage. This is accurately described as **tamper-evident**, not immutable.

## Current limitation and compensating control

A sufficiently privileged host administrator could replace the entire chain and recompute it. For a pilot, export the verified chain head after each evidence hand-off and store it on separately administered, approved write-once or immutable storage. That external witness adds a genuinely separate trust boundary; running another ledger process on the same laptop does not.

## When the decision should change

Reconsider an external ledger only when all of the following are true:

- multiple agencies independently write or attest to the same custody history;
- no single agency is permitted to rewrite the shared history;
- governance defines membership, revocation, retention, legal discovery and incident recovery;
- the deployment provides independently administered validator nodes and protected signing keys; and
- performance and personal-data impact have been approved.

At that point, anchor only salted evidence digests, event hashes and periodic chain-head checkpoints. Do not place FIR text, identities, phone numbers, victim information or other personal data on-chain. A permissioned consortium ledger or agency-approved immutable timestamping service would be more appropriate than a public cryptocurrency network.

## SIH claim boundary

The cybersecurity contribution today is verifiable chain of custody, provenance hashes, role-gated actions, protected-person controls and explicit audit verification. Sentinel does not claim blockchain deployment, and the absence of blockchain is a threat-modelled engineering decision rather than an omitted feature.
