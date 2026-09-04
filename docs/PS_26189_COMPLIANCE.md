# PS 26189 — Pinnacle Coverage Matrix

**Problem:** AI-Powered Criminal Network Analysis System  
**Organization:** Ministry of Home Affairs  
**Department:** NCRB, Women Safety Division  
**Build date:** 04 September 2026  
**Operating target:** free, offline-capable single-machine demonstration plus a synthetic-only public web edition

## Evaluation summary

Sentinel implements the complete judge-visible workflow: ingest evidence, verify integrity, extract typed entities, build an ontology-aligned graph, rank key individuals, detect suspicious patterns, explain findings, and export an investigator brief. Operation Suraksha makes that workflow demonstrable across six synthetic evidence channels, with declared ground truth and a deliberate negative identity control. Every analytical screen is driven by the active graph. Observations, derived indicators, model outputs, and hypotheses are labelled separately.

## Requirement-to-evidence mapping

| Problem-statement requirement | Runtime implementation | Judge-visible proof |
| --- | --- | --- |
| Collect and process multiple sources | Working FIR, CDR, banking, ANPR, surveillance, and OSINT-shaped records; CSV/JSON adapters; deterministic FIR parser; XML profiling; RDF/TTL semantic intake; upload controls; SHA-256 fingerprinting | Fusion replay source counter and stages; Data ingestion → run pipeline → verified output and live log |
| Extract people | Named suspects and common person/caller/sender/beneficiary fields become `person` nodes | Graph filter: Person; entity dossier shows source-derived description |
| Protect victims/survivors | `protected_person` is distinct from a suspect; masked by default; risk fixed at zero; excluded from influence ranking and GraphSAGE | Fusion replay → Protected-person privacy; reason and authorization reference are required for an ephemeral synthetic reveal |
| Extract locations | Blocks, addresses, towers, and police beats become `location` nodes | Graph filter: Location; Geo intelligence ranks active operational areas |
| Extract vehicles | FIR plates and vehicle fields become `vehicle` nodes | Search a supplied plate such as `IL-4258-DT` |
| Extract phone numbers | CDR aliases (`caller_number`, `callee_number`, `msisdn`, etc.) become `phone` nodes | Upload a CDR-shaped CSV; Phone appears in graph legend and nodes |
| Extract organizations | Organization/company/employer/merchant fields become `organization` nodes | Upload a transaction/OSINT-shaped CSV and filter Organization |
| Build relationship maps | Ontology predicates plus generic observed-source predicates produce directed graph edges | Graph explorer, relationship dossier, JSON and GraphML exports |
| Identify influential individuals | Person-only degree, sampled Brandes betweenness, reach, and composite influence | Advanced analytics → Influential people → switch ranking method |
| Detect suspicious patterns | Explainable risk rules, circular transfers, time-window convergence, repeat-subject/location detection, temporal motifs, anomaly links, GraphSAGE suspect classifier | Fusion replay, Risk panel, Alert center, GraphSAGE panel, TRACE Lab motif radar |
| Discover hidden links | Cross-source bridge discovery, feature-overlap candidate ranking with every signal exposed, and stored-edge path proving for known connectivity | Operation Suraksha recovers the declared Subject A-17 → Coordinator C-04 path; TRACE exposes every hop and receipt |
| Prevent unsafe identity linkage | Candidate merge shows support and contradictions; name-only match is rejected; only a human can keep separate or request more verification | Fusion replay → Entity resolution control; Kavya Rao and K. Rao remain distinct nodes |
| Provide visual and analytical insight | Interactive graph, source timeline, concentration grid, risk trajectory, distributions, communities, findings | Command center and Advanced analytics |
| Produce actionable intelligence | Findings contain evidence, alternative explanations, confidence, and next human action | Review analysis → Explain finding; report export |

## Trust and cybersecurity controls

- All core processing runs locally; no paid or cloud API is required.
- Uploaded filenames are path-normalized and size-limited; active graph snapshots use atomic file replacement.
- Every evidence input receives a SHA-256 digest.
- Investigation actions form an append-only SHA-256 chain covering uploads, activations, identity decisions, protected reveals, alert acknowledgement, exports, and resets; `/api/audit/verify` detects content or linkage changes.
- API responses use no-store, no-sniff, frame-deny, no-referrer, and restrictive permissions headers.
- The frontend deployment includes a Content Security Policy.
- Arbitrary login credentials are rejected; demo credentials and signing secrets are environment-configurable.
- GraphSAGE checkpoints load with `weights_only=True`.
- The model refuses inference on out-of-training-schema graphs and shows a structural preview instead.
- Protected-person nodes are removed before all model feature generation and can never receive model probabilities.
- Risk scores and new link candidates cannot trigger automated enforcement.
- TRACE results include deterministic SHA-256 receipts, alternative explanations, and explicit observation/derivation labels.
- Entity-resolution candidates never auto-merge graph nodes; analyst actions are locally receipted and preserve the source graph.

## Truth boundary

| Output class | Meaning |
| --- | --- |
| Observation | Direct source field, source count, or direct graph relationship |
| Derived indicator | Deterministic aggregation, risk rule, topology metric, or model score |
| Hypothesis | Suggested relationship requiring independent source verification |
| Decision | Reserved for an authorized human investigator |

The geographic view uses a deterministic operational display grid because the supplied dataset has police beats and blocks but no source latitude/longitude. Its proxy coordinates are marked “not source GPS” in the UI and GeoJSON properties.

## Verified acceptance checks

- Backend: 25 API/unit tests covering graph loading, FIR parsing, generic CDR/financial mapping, active investigation switching, GraphSAGE behavior, source-derived analytics, TRACE proof outputs, Operation Suraksha acceptance truth, protected-person policy, audit tamper detection, safe reset, provenance, exports, and credential rejection.
- Frontend: 3 component tests covering the command center, explainable briefing, and interactive Fusion Room.
- Production frontend build passes under React 19.2 and supported Vite 6.4.
- Frontend dependency audit reports zero known vulnerabilities.
- Flagship demo: 32 synthetic records → 64 entities → 148 relationships; 14/14 entity checkpoints, 6/6 relation checkpoints, hidden path recovered, zero false merges.
- Larger validation investigation: 500 supplied records → 1,530 entities → 2,127 relationships.
- Scale harness: 100,000 synthetic records → 104,256 nodes and 400,000 edges in 80.838 seconds on the documented laptop; limitations are stated in `SUBMISSION_EVALUATION.md`.

## Deployment boundary

The complete React/FastAPI product can run from one public Docker web service for the internal round. Its public mode is synthetic-only and blocks uploads; free-host filesystem changes are ephemeral. This remains a competition prototype—not a certified law-enforcement system. Multi-user operational deployment still requires agency identity integration, malware scanning, key management, database adapter activation, retention policy, jurisdiction-specific privacy controls, independent model validation, and red-team/security accreditation.
