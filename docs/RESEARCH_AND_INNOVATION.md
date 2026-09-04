# Research and Innovation Positioning

**Assessment date:** 04 September 2026  
**Scope:** SIH 26189 — AI-Powered Criminal Network Analysis System  
**Constraint:** free, offline-capable, single-machine demonstration

## Product thesis

Many investigation demos can draw a network or place an LLM chat box beside it. Sentinel's distinguishing idea is **proof-carrying intelligence**: every consequential analytical result must expose how it was produced, what was actually observed, what was derived, what could be wrong, and a deterministic receipt for reproducing the output.

This is implemented as **TRACE** (Transparent Relationship, Assumption, Corroboration, and Evidence) Lab:

1. **Relationship proof:** weighted shortest paths traverse only stored graph edges and expose every node, relationship, direction, and confidence.
2. **Temporal motifs:** repeat-subject, rapid-repeat, and operational-area concentration patterns are computed from source timestamps and direct neighborhoods.
3. **Counterfactual stress tests:** an analyst can see how correcting an identity, arrest state, domestic marker, weapon descriptor, or duplicate location assignment changes the encoded risk score.
4. **Epistemic boundary:** observations, derived leads, hypotheses, and human decisions are never presented as the same thing.
5. **Reproducibility receipt:** canonical result payloads receive SHA-256 digests so reruns can be compared precisely.
6. **Record-level provenance:** every relationship names its source channel, record identifier, observation time, and canonical record digest.
7. **Claim-aware ML:** a machine-readable model passport separates a reproducible structural-proxy result from unestablished field accuracy.

The companion **Operation Suraksha Fusion Room** turns those principles into a judge-visible exercise: six synthetic evidence channels, a known hidden path, declared acceptance truth, and an ambiguous-name case that the system must refuse to auto-merge.

This design is inspired by work on inherently explainable temporal graph models and explainable temporal rule paths, while deliberately using a deterministic, inspectable implementation suitable for an SIH demo and ordinary CPU hardware. The scan covers public material found by the assessment date; it is a product-positioning review, not a claim that every 2025–2026 publication has been exhaustively surveyed.

## Competitive scan

| Reference | Useful ideas observed | Sentinel position |
| --- | --- | --- |
| [Criminal Network Analysis and Visualization](https://github.com/erichoang/criminal-network-visualization) | Community detection, social influence, embeddings, and transductive/inductive link prediction; tied to a 2023 Journal of Computational Science paper | Sentinel includes active-graph topology, centrality, GraphSAGE integration, explainable candidate links, and an end-to-end evidence workflow; TRACE adds proof and counterfactual layers around outputs |
| [TATVA Forensic Investigation](https://github.com/rio-ARC/TATVA-Forensic-Investigation) | CDR, bank, GPS, email, and FIR preprocessors; entity resolution; smurfing, cycles, and co-location; 3D graph and dossier output | Sentinel implements explicit CDR/transaction/FIR/OSINT field mapping locally. Its core path has no Gemini, Supabase, AuraDB, or Upstash requirement and focuses on reproducible evidence rather than cloud narrative generation |
| [IBM AMLSim](https://github.com/IBM/AMLSim) | Multi-agent generation of synthetic banking transactions containing known laundering patterns | Recommended optional financial scenario generator; not silently bundled into the current evidence corpus |
| [IBM AML-Data](https://github.com/IBM/AML-Data) | Labeled, fully synthetic transaction data representing legitimate and laundering behavior | Recommended optional benchmark for transaction-pattern evaluation. Repository code is Apache-2.0; the dataset is CDLA-Sharing-1.0 and must retain its license |
| [Indic TrOCR](https://github.com/iitb-research-code/indic-trocr) | Apache-2.0 transformer OCR for handwritten documents in Indian languages | Strong optional extension for scanned FIR intake; it needs a separately tested model/runtime profile before being called integrated |

The comparison is based on public repository documentation, not on claims that Sentinel has copied or absorbed those codebases.

## Research basis

- [Self-Explainable Temporal Graph Networks](https://arxiv.org/abs/2406.13214) (KDD 2024) motivates time-aware graph representations whose explanations are part of the model rather than a detached afterthought. TRACE applies that product principle with source-timestamp motifs and evidence-first output.
- [TLogic: Temporal Logical Rules for Explainable Link Forecasting on Temporal Knowledge Graphs](https://arxiv.org/abs/2112.08025) motivates time-consistent, rule-grounding paths that make a forecast inspectable. Sentinel does not claim to implement TLogic; it borrows the stricter idea that a graph lead should carry a traversable path and explicit status.
- [Self-Exploring Language Models for Explainable Link Forecasting on Temporal Graphs](https://arxiv.org/abs/2509.00975) (2025) evaluates reasoning traces and hallucination effects alongside ranking quality. It strengthens Sentinel's choice to keep generated prose outside the evidence layer and make replay receipts deterministic.
- [Towards Foundation Model on Temporal Knowledge Graph Reasoning](https://arxiv.org/abs/2506.06367) (2025) targets fully inductive transfer across unseen entities, relations, and timestamps. Sentinel does not claim that capability; active-investigation switching and schema-compatibility refusal are the honest local foundations for future cross-domain validation.
- [Investigating the Robustness of Graph Neural Networks to Data Drift](https://ieeexplore.ieee.org/document/11172673/) (IEEE Access, 2025) reports degradation across temporal windows even when GraphSAGE is comparatively robust. Sentinel therefore exposes model provenance and schema compatibility instead of treating one validation score as permanent operational assurance.

## Dataset strategy

| Dataset/source | Correct use | Incorrect use to avoid |
| --- | --- | --- |
| Operation Suraksha synthetic fixture | Flagship cross-source fusion, ground-truth acceptance checks, identity-resolution safety demo | Presenting fictional people, identifiers, Bengaluru locations, or scores as operational data or independent accuracy evidence |
| Supplied 500-record crime corpus and FIR text | Primary entity-level demo graph and GraphSAGE reproduction | Presenting it as Indian police operational data |
| [NCRB Crime in India 2023 resources](https://www.data.gov.in/resource/crime-head-wise-and-stateut-wise-special-and-local-laws-sll-crimes-during-2023) | Official aggregate reference for state/city/offense baselines and contextual dashboard benchmarks | Fabricating person-to-person edges from aggregate statistics; the resource is annual aggregate data and notes that states/UTs should not be compared purely by crime figures |
| IBM AMLSim / IBM AML-Data | Synthetic financial network scenarios and labeled evaluation | Mixing generated entities into a live case without a visible synthetic-data boundary |
| Agency-provided CDR, transaction, surveillance, social, and FIR exports | Real pilot validation after legal authorization, schema review, redaction, and retention controls | Scraping or collecting personal data without authority |

Sentinel ships the user-supplied artifacts plus the explicitly fictional Operation Suraksha fixture and its separate ground-truth file. External candidates above are a documented validation roadmap, not a false claim of integration.

## Why the build remains free

The evaluation path uses React, FastAPI, deterministic Python graph analysis, local JSON investigation snapshots, the supplied ontology, and CPU GraphSAGE inference. No paid API key, hosted LLM, managed database, or internet connection is required. Docker services are optional deployment adapters, not prerequisites for the one-machine demonstration.

## Judge-facing novelty demonstration

1. Open **Fusion replay** and activate Operation Suraksha.
2. Reveal the FIR, CDR, banking, ANPR, surveillance, and OSINT stages.
3. Show the 14/14 entity, 6/6 relationship, and 5/5 computed-pattern acceptance results plus 100% edge provenance.
4. Demonstrate why the Kavya Rao / K. Rao candidate stays separate despite name similarity.
5. Open **TRACE Lab** and show the exact stored-edge path from Subject A-17 to Coordinator C-04.
6. Connect the proof back to the entity dossier, temporal motifs, and counterfactual checks.
7. Switch to Operation City Shield or a newly ingested dataset to prove the workflow is active-graph-driven rather than a one-screen animation.

The key pitch is: **Sentinel does not merely produce an answer; it produces an answer that can be challenged.**

## Honest boundary

This is designed to be a standout competition prototype and a serious local-pilot foundation, not a certified production law-enforcement system. Operational deployment still requires agency identity integration, access-policy enforcement, malware scanning, encryption/key management, audit immutability, jurisdiction-specific privacy controls, retention and deletion policy, independent bias/model validation, and formal security accreditation.
