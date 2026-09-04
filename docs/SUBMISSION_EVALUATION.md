# Sentinel submission evaluation

**Problem statement:** SIH 26189 — AI-Powered Criminal Network Analysis System  
**Evaluation date:** 05 September 2026
**Claim boundary:** Competition prototype evaluated on supplied and synthetic data; not an operational police certification.

## Acceptance results

| Evaluation | Result | Reproducible proof |
| --- | ---: | --- |
| Six-source flagship ingestion | 32/32 records | `operation_suraksha.json` and Fusion Room source counts |
| Cross-source pattern acceptance | 5/5 patterns | Runtime detectors for call burst, repeat transfers, account cycle, time/location convergence, and bridge entity |
| Relationship provenance | 148/148 edges | Source record ID, channel, timestamp, and canonical SHA-256 record digest |
| Required entity checkpoints | 14/14 | Separate ground-truth fixture and `/api/demo/suraksha/evaluation` |
| Required relationship types | 6/6 | Same endpoint; includes protected-person linkage |
| Hidden Subject A-17 → Coordinator C-04 path | Recovered | TRACE stored-edge path with SHA-256 receipt |
| False merge negative control | 0 | Kavya Rao and K. Rao remain distinct |
| Protected-person risk/ML exposure | 0 | Two nodes fixed at risk 0 and removed before model feature generation |
| Tamper-evident audit | Valid | `/api/audit/verify` recalculates sequence, previous hash, and content hash |
| Larger supplied corpus | 500 records | 1,530 nodes and 2,127 relationships |
| Backend verification | 34 tests passed, 1 integration test conditionally skipped locally | `pytest -q`; hybrid persistence runs with service containers in CI |
| External audit witness | Real calendar submission verified; initial state correctly remains pending | OpenTimestamps `.ots` proof and `/api/audit/anchors`; Bitcoin aggregation is asynchronous |
| Frontend verification | 5 tests passed | `npm test`; all eleven routes also pass a 430 px viewport overflow/target-size audit |
| Private access boundary | Passed | mandatory JWT mode, analyst/supervisor separation, protected reveal denial for analyst |
| Model evaluation | Leakage-audited, claim-bounded | Perfect reproduction result quarantined; ten-trial 20% evidence-masking stress F1 `0.825` mean (`0.780–0.849`); field accuracy not established |
| Hybrid persistence | CI-verified | Real PostgreSQL and Neo4j round trip with two case-isolated graphs |

The deployable NumPy GraphSAGE forward pass was compared across all 434 suspect nodes with the PyTorch Geometric implementation: maximum probability delta `0.0`, with identical classifications. The lightweight artifact enables real checkpoint inference on the free web image while the training notebook and full ML runtime remain available locally. The version-2 model artifact explicitly records target/input dependency and checkpoint-selection leakage; no perfect metric is presented as field performance.

## Scale evidence from this machine

The benchmark generates deterministic CDR-shaped records in memory and executes the real `build_multisource_graph` and `connection_path` code paths. Generated source records are not retained.

| Records | Graph nodes | Graph edges | Build | Throughput | Peak Python allocation | Search p95 | Path p95 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10,000 | 14,256 | 40,000 | 9.529 s | 1,049.4 records/s | 76.13 MiB | 12.088 ms | 331.593 ms |
| 100,000 | 104,256 | 400,000 | 80.838 s | 1,237.0 records/s | 700.25 MiB | 44.225 ms | 1,833.464 ms |

Environment: Python 3.11.9 on Windows, Intel64 Family 6 Model 170. Memory is `tracemalloc` peak, not total process RSS. Results are single-process, single-user measurements and do not claim distributed scale. The raw result is in `backend/benchmarks/scale_results.json`; rerun with `python backend/scripts/benchmark_scale.py`.

Entity-resolution precision is intentionally reported as **not applicable**: Sentinel performs no automatic identity merge, so it abstains instead of manufacturing a precision number. Across 200 generated negative-control pairs, automatic merges = 0 and false merges = 0. Identity decisions require a human rationale and enter the audit chain.

## Differentiation without overclaiming

| Capability | Manual spreadsheet review | Graph-only dashboard | Cloud LLM copilot | Sentinel |
| --- | --- | --- | --- | --- |
| Multi-source evidence linkage | Labor intensive | Usually supported | Depends on retrieval layer | Working six-source fixture and upload adapters |
| Inspectable path proof | Manual | Often graph-visible | May summarize without a stable proof object | Every TRACE hop is a stored edge with a receipt |
| Protected-person entity policy | Process dependent | Product dependent | Prompt/policy dependent | Separate type, masked default, risk 0, ML exclusion |
| Identity resolution | Manual judgment | Product dependent | Risk of confident name-based suggestions | Contradictions visible; no automatic merge |
| Tamper evidence | External process | Product dependent | Product dependent | Local SHA-256 chain plus optional blinded OpenTimestamps/Bitcoin checkpoint |
| Works without paid APIs | Yes | Product dependent | Usually no | Yes |
| Natural-language presentation | Manual | Limited | Strong | Deterministic evidence-backed briefing, no hallucinated facts |
| Public demonstration safety | Depends on operator | Depends on product | Data-egress risk | Synthetic-only deployment mode blocks uploads |

This comparison describes architectural categories, not audited claims about named competitors.

## Known limits and next production gates

- Public free hosting has ephemeral local storage; audit events, decisions and timestamp proofs reset on service restart. Download checkpoint/proof pairs immediately; the private build persists them locally.
- The 100k benchmark proves bounded single-machine behavior, not concurrent casework or national-scale throughput.
- The GraphSAGE checkpoint reproduces the supplied notebook's label rule and split; it is not independently validated on operational Indian data.
- The synthetic protected-person vault proves the interaction and audit policy, not compliance with an agency's final authorization model.
- The private pilot now provides local JWT authentication, analyst/supervisor authorization, persistent Docker state, PostgreSQL catalogue, case-scoped Neo4j mirroring, rate limits and operational probes. Agency production still requires identity-provider federation, encryption key management, approved malware scanning, durable object storage, retention/deletion policy, approved redacted datasets, fairness testing, penetration testing, and formal accreditation.

## Submission decision

For a college internal SIH round, the build is submission-ready at its live Render URL. It is best described as a deployment-ready investigative pilot rather than a mock-up. The strongest demonstration is not feature count: it is the complete chain from six fragmented sources to a challengeable graph finding, followed immediately by the privacy guardrail, false-merge prevention, and valid audit-chain proof.
