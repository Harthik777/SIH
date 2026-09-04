# Sentinel Knowledge Graph Investigation Platform

Sentinel is a full-stack investigation workspace that turns FIR narratives and structured crime records into an ontology-aligned knowledge graph. It combines a fast investigator-facing interface with a FastAPI service for ingestion, graph exploration, analytics, anomaly review, explanations, and export.

The September 2026 build is designed as an award-ready, zero-cloud SIH demonstration: it runs on one machine, requires no paid API, fingerprints every evidence artifact, separates observations from hypotheses, and keeps a human analyst in control of every consequential interpretation.

The repository opens with **Operation Suraksha**, a clearly labelled fictional Bengaluru-area exercise built to prove multi-source fusion safely:

- 32 synthetic records across FIR, CDR, banking, ANPR, surveillance, and OSINT-shaped evidence
- 62 typed entities and 146 source-linked relationships
- 12/12 entity and 5/5 relationship acceptance checkpoints recovered
- one hidden cross-source path, one circular account pattern, and one deliberate false-identity-merge trap
- a six-stage judge replay with deterministic receipts and an explicit no-real-person boundary

The supplied Chicago crime corpus remains available as **Operation City Shield**, a larger validation investigation:

- 500 FIR narratives
- 500 structured crime records
- 434 unique named suspects
- 104 extracted vehicle plates
- 462 location blocks and 22 police beats
- 8 crime categories
- the source and populated WebProtégé crime ontologies

## Run locally

Prerequisites: Node.js 20+ and Python 3.11+.

```powershell
npm run install:all
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). The API is at [http://localhost:8000](http://localhost:8000), and its interactive OpenAPI documentation is at [http://localhost:8000/docs](http://localhost:8000/docs).

The frontend has a deterministic fallback dataset, so it still renders if the API is temporarily unavailable. Start just the UI with `npm run dev:frontend` or just the API with `npm run dev:api`.

## Run the complete stack

Docker Compose starts the web app, API, Celery worker, PostgreSQL, Neo4j, and Redis:

```powershell
docker compose up --build
```

Services:

| Service | Address | Purpose |
| --- | --- | --- |
| Web app | `localhost:5173` | React investigator console |
| API | `localhost:8000` | FastAPI + WebSockets |
| API docs | `localhost:8000/docs` | OpenAPI explorer |
| Neo4j Browser | `localhost:7474` | Graph database console |
| Neo4j Bolt | `localhost:7687` | Graph driver connection |

Copy `.env.example` to `.env` before using non-demo credentials.

## Product capabilities

- Drag-and-drop CSV, JSON, TXT, XML, RDF, and TTL ingestion
- Five-stage processing with real source profiling, SHA-256 fingerprints, streamed logs, and measured graph output
- Automatic FIR narrative extraction plus explicit field mapping for CDR, transaction, surveillance, and OSINT-shaped CSV/JSON records
- Durable local investigation snapshots with an active-investigation selector; a processed graph immediately drives every downstream view
- Operation Suraksha Fusion Room: a six-stage cross-source replay, synthetic ground-truth scorecard, hidden-network reveal, and safe entity-resolution decision control
- Interactive Cytoscape knowledge graph with search, type filters, layouts, zoom, and entity dossiers
- Source-derived timeline and police-beat concentration views with non-GPS proxy coordinates labelled explicitly
- Active-graph risk scoring, anomaly triage, persisted-in-session alert acknowledgement, and natural-language explanations
- Key-individual rankings using degree, deterministic sampled betweenness, reach, and composite influence
- Communities, type distributions, exact degree distribution, modularity, and clearly labelled topology visualization
- GraphSAGE suspect-risk feature preparation, model status, and optional checkpoint inference
- Expandable finding rationale with source records, alternatives, limitations, and human-review actions
- Evidence Trust Center with data-quality, provenance, model-readiness, and decision-policy gates
- Transparent case↔subject link hypotheses whose supporting feature overlaps are inspectable
- TRACE proof-carrying intelligence with observed connection paths, temporal motifs, counterfactual risk checks, explicit alternative explanations, and deterministic SHA-256 receipts
- Conservative entity resolution that surfaces supporting and conflicting signals, prevents name-only auto-merges, and reserves identity decisions for humans
- JSON, GraphML, CSV, GeoJSON, and generated PDF exports
- Dark/light themes and responsive navigation
- JWT-compatible local authentication that rejects arbitrary credentials, plus role-ready persistence models
- PostgreSQL metadata schema, batch-safe Neo4j adapter, Redis/Celery worker, and Docker deployment

## Data and ontology integration

The flagship scenario lives in [`backend/data/operation_suraksha.json`](backend/data/operation_suraksha.json), with its separately declared acceptance truth in [`backend/data/operation_suraksha_ground_truth.json`](backend/data/operation_suraksha_ground_truth.json). The runtime builds the graph from those records; replay and evaluation values are computed from the resulting graph rather than hard-coded success counters. The scenario is fictional and must never be represented as NCRB case data.

The same active-graph pipeline also reads [`backend/data/crime_dataset.csv`](backend/data/crime_dataset.csv) for Operation City Shield and maps each record to the supplied ontology:

```text
CrimeIncident ──HAS_SUSPECT────────> Suspect
      │                                  │
      ├──HAS_CRIME_TYPE──> CrimeType     └──DRIVES_VEHICLE──> Vehicle
      ├──OCCURRED_AT─────> Location
      └──OCCURRED_IN_BEAT> PoliceBeat
```

Risk is deliberately explainable. It starts from offense severity, then applies explicit adjustments for armed descriptions, arrest state, domestic-dispute markers, repeat subjects, and repeat locations. The output is suitable for analyst prioritization, not automated guilt or enforcement decisions.

The original supplied scripts are preserved in `backend/reference/`. The runtime adapter fixes a defect in the original graph builder where a vehicle node was created outside the `vehicle_plate` conditional; records without a plate could otherwise reference an undefined or stale `plate` value.

## GraphSAGE model integration

The supplied [`GraphSAGE_Model.ipynb`](backend/models/GraphSAGE_Model.ipynb) is integrated as a two-layer suspect classifier with the exact notebook schema: six one-hot ontology node types plus normalized node degree, 32 hidden channels per layer, and `normal` / `suspicious` outputs. Its source graph and the separately supplied link-prediction JSON are preserved alongside it in `backend/models/`.

The notebook saves `graphsage_model.pt`, but that checkpoint was not included in the supplied files. A fresh checkpoint has therefore been reproduced from the notebook architecture and matching source graph with a fixed split seed (`42`) and model seed (`1`). The selected epoch achieved validation F1 `1.0` on the notebook's 80/20 suspect split; provenance is recorded in `backend/models/graphsage_training.json`. This is a reproduction, not the notebook author's original serialized state.

`/api/analytics/graphsage` performs real CPU inference whenever the checkpoint and optional PyTorch Geometric runtime are available. If either is absent, it returns a clearly labelled structural feature preview—never fabricated model probabilities. Checkpoints are loaded with `weights_only=True`.

```powershell
npm run install:ml
python backend/scripts/train_graphsage.py --epochs 200 --seed 1
```

The notebook-reported validation score is retained as training metadata, not presented as an independent test result. Model outputs are decision support for analyst review and are not evidence of guilt.

## Evidence integrity and responsible analysis

`/api/provenance/manifest` creates a local chain-of-custody manifest for the dataset, FIR corpus, ontology, model graph, training notebook, reproduced checkpoint, and supplied output. Each entry includes its complete SHA-256 digest, byte size, modification time, role, and a [W3C PROV-O](https://www.w3.org/TR/prov-o/) compatible type.

The platform maintains explicit epistemic boundaries:

- observed source fields and direct counts are presented as evidence;
- rule-based scores and GraphSAGE outputs are presented as derived indicators;
- new links from `/api/analysis/link-candidates` are labelled hypotheses, not facts;
- the supplied 50-row link output is retained but marked non-actionable because all scores are identical and below threshold;
- every consequential finding includes alternative explanations and a required human verification step.

Both built-in investigations pass their schema-specific data-quality gates. Operation Suraksha additionally evaluates itself against a transparent synthetic ground truth; those checks establish scenario reproducibility, not real-world model accuracy.

## PS 26189 coverage

This build is mapped directly to the Ministry of Home Affairs / NCRB problem statement:

| Required capability | Implemented evidence |
| --- | --- |
| Process multiple sources | Working FIR/CDR/banking/ANPR/surveillance/OSINT synthetic exercise, CSV and JSON schema mapping, FIR text extraction, XML profiling, RDF/TTL semantic intake, SHA-256 provenance |
| Extract people, places, vehicles, phones, and organizations | Typed ontology nodes for `person`, `location`, `vehicle`, `phone`, `organization`, `account`, `event`, and `crime` |
| Build relationship maps | Active Cytoscape graph plus JSON/GraphML export and ontology-labelled predicates |
| Identify key individuals | Person-filtered degree, sampled betweenness, neighborhood reach, and composite influence rankings |
| Detect suspicious patterns | Transparent risk rules, time-window convergence, account-cycle replay, repeat-entity and concentration alerts, GraphSAGE inference, and explainable link candidates |
| Give actionable investigator insight | Evidence-backed brief, alternatives, provenance, timeline, concentration grid, source links, and required human next actions |

The detailed verification matrix is in [`docs/PS_26189_COMPLIANCE.md`](docs/PS_26189_COMPLIANCE.md).
The GitHub, research-paper, and dataset landscape behind the differentiation strategy is in [`docs/RESEARCH_AND_INNOVATION.md`](docs/RESEARCH_AND_INNOVATION.md).

## Important paths

```text
frontend/src/
├── components/              Investigator UI modules
├── data/mockData.ts         Offline UI fallback
├── api.ts                   Typed API adapter
└── styles.css               Responsive design system

backend/
├── app/main.py              REST, WebSocket, analytics, and exports
├── app/crime_pipeline.py    FIR extraction and graph construction
├── app/investigation_store.py Durable local active-graph workspace
├── app/network_intelligence.py Source-derived topology, timeline, map, and alerts
├── app/trace_engine.py        Proof paths, temporal motifs, counterfactuals, receipts
├── app/suraksha.py            Flagship replay, ground-truth evaluation, identity controls
├── app/database.py          PostgreSQL models + Neo4j repository
├── app/celery_app.py        Redis/Celery task entry point
├── data/                    Synthetic flagship fixtures plus supplied CSV/FIR corpus
├── models/                  GraphSAGE notebook, graph, outputs, and checkpoint slot
├── ontology/                Source and populated TTL ontologies
└── reference/               Original supplied Python scripts
```

## API overview

The API includes all requested route groups:

- `/api/upload`, `/api/uploads`, `/api/upload/{id}`
- `/api/pipeline/start`, `/api/pipeline/status/{id}`, `/api/pipeline/stream/{id}`
- `/api/graph/nodes`, `/api/graph/edges`, `/api/graph/subgraph`, `/api/graph/search`, `/api/graph/metrics`
- `/api/investigations`, `/api/investigations/active`, `/api/investigations/{id}/activate`
- `/api/demo/suraksha/replay`, `/api/demo/suraksha/evaluation`
- `/api/entity-resolution/candidates`, `/api/entity-resolution/{id}/decision`
- `/api/analytics/centrality`, `/api/analytics/key-individuals`, `/api/analytics/community`, `/api/analytics/embeddings`, `/api/analytics/distribution`, `/api/analytics/trends`, `/api/analytics/graphsage`
- `/api/analysis/anomalies`, `/api/analysis/risk-scores`, `/api/analysis/link-predictions`, `/api/analysis/link-candidates`, `/api/analysis/briefing`, `/api/analysis/explanations/{id}`
- `/api/analysis/connection-path`, `/api/analysis/motifs`, `/api/analysis/counterfactual/{id}`, `/api/analysis/trace/{id}`
- `/api/visualization/graph`, `/api/visualization/timeline`, `/api/visualization/locations`, `/api/visualization/heatmap`
- `/api/export/graph/json`, `/api/export/graph/graphml`, `/api/export/report/pdf`, `/api/export/data/csv`, `/api/export/geojson`
- `/api/data/quality`, `/api/provenance/manifest`
- `/api/config`, `/api/models`, `/api/models/graphsage/status`, `/api/ontology/summary`, `/api/auth/login`, `/api/auth/me`

## September 2026 frontend baseline

The UI uses React 19.2.8. Vite is pinned to the supported 6.4 security-maintenance line because the target machine currently runs Node 20.16; this avoids requiring a machine-wide Node upgrade while retaining security patches. Vitest 3.2.7 replaces the vulnerable older test runtime, and `npm audit` reports zero known frontend dependency vulnerabilities.

## Tests

```powershell
npm test
```

This runs the frontend component tests and backend API tests. A production frontend build can be checked separately with `npm run build`.

## Production notes

The default API graph store is durable local JSON with atomic replacement, designed for free single-machine evaluation. `Neo4jGraphRepository` provides indexed, batched persistence for deployment. PostgreSQL ORM models cover users, uploads, processing logs, investigations, alerts, and saved filters. Before multi-user deployment, wire those adapters into the request dependency layer, rotate the JWT secret and local demo password, use password hashing or identity federation, and place object storage and malware scanning in front of raw uploads.
