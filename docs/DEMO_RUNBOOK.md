# Sentinel 5-minute SIH flagship demo

## One-line pitch

Sentinel fuses disconnected evidence into proof-carrying investigative leads: every path can be inspected, every inference can be challenged, and every consequential decision stays with a human—fully local and without paid APIs.

## Before judges arrive

1. Run `npm run dev` and open `http://localhost:5173`.
2. Open **Fusion replay** and activate **Operation Suraksha** if it is not already active.
3. Click **Reset**, then **Start guided demo**. Keep browser zoom at 100% and confirm the scorecard reads `14/14`, `6/6`, `YES`, and `0`.
4. Do not describe the scenario as real NCRB data. It is a deliberately fictional Bengaluru-area acceptance exercise.

## Demo flow

1. **Start with the reveal (75 seconds)**
   - Open **Fusion replay**.
   - Say: “These are 32 fictional records that look like six disconnected evidence exports: FIR, CDR, bank, ANPR, surveillance, and OSINT preservation.”
   - Click **Reveal next signal** through the stages: pre-incident call burst, circular account path, time-window convergence, and bridge entity.
   - Point out that each stage carries a SHA-256 receipt and source-backed object IDs.

2. **Show protected-person privacy (45 seconds)**
   - Scroll to **Protected-person privacy** and show the masked identity.
   - Point out that protected people have their own graph type, risk scoring is prohibited, and GraphSAGE never receives those nodes.
   - Enter the pre-filled reason and authorization reference, reveal the fictional identity, then mask it again. Show that the audit-chain count increases.

3. **Show the identity safety differentiator (45 seconds)**
   - At stage six, show `Kavya Rao` and `K. Rao`.
   - Explain that name similarity suggests a candidate, but distinct phones and incompatible near-simultaneous locations contradict a merge.
   - Click **Keep separate**. State: “The system cannot silently collapse identities; it records a human review decision and leaves both nodes separate.”

4. **Prove the hidden connection (60 seconds)**
   - Select **Open path proof** to enter **TRACE Lab**.
   - Choose `Subject A-17` and `Coordinator C-04`, then calculate the path.
   - Walk through the stored edges and show the path receipt. Distinguish observations from derived leads and hypotheses.

5. **Show the full investigation workspace (60 seconds)**
   - Open **Graph explorer** and search for `Coordinator C-04`.
   - Show links across phones, accounts, the shared vehicle, organization, locations, and events.
   - Open **Advanced analytics** to show centrality and topology. Explain that the supplied GraphSAGE model refuses to claim compatible inference on this richer schema and labels the output `schema-incompatible-preview`.

6. **Show transfer to new evidence (45 seconds)**
   - Open **Data ingestion** and explain the CSV/JSON/TXT/XML/RDF/TTL path.
   - Show source fingerprinting, measured output counts, active-investigation switching, and the fact that a processed graph drives all downstream screens.

7. **Close with operational output (15 seconds)**
   - Open **Reports & exports** and show JSON, GraphML, CSV, GeoJSON, and PDF outputs.
   - Close with: “Sentinel does not merely output an answer; it outputs an answer an investigator can challenge.”

## Architecture answer

```text
React investigator console
        │ local REST / WebSocket
        ▼
FastAPI evidence + analytics service
        ├── multi-source extraction and ontology alignment
        ├── active knowledge graph + NetworkX analytics
        ├── TRACE paths, motifs, counterfactuals, receipts
        ├── safe entity-resolution review
        └── optional CPU GraphSAGE inference

Optional deployment adapters: Neo4j, PostgreSQL, Redis, Celery
```

## Judge questions

**Why did you not add a cloud LLM?**  
The core task is evidence linkage, not fluent text generation. A cloud LLM would add cost, data-egress risk, non-determinism, and a new hallucination surface. Sentinel already produces templated natural-language explanations from traceable graph facts. A locally hosted, access-controlled language interface can be added later, but it must never become the evidence source or identity decision-maker.

**Are the evaluation numbers real?**  
They are real acceptance results against the declared synthetic Operation Suraksha ground truth: 14/14 entity checkpoints, 6/6 relation types, the intended hidden path recovered, and zero false merges. The 10k/100k numbers are measured on the documented machine. None are presented as accuracy on operational police data.

**Does it require internet or paid APIs?**  
No. Runtime processing, graph analytics, model inference, provenance, replay, and report generation run locally. The internal-round public URL hosts the same complete web app; the offline edition still works when internet access is unavailable.

**Can it scale beyond one machine?**  
The measured single-process harness built 100,000 synthetic records into 104,256 nodes and 400,000 edges in 80.838 seconds on the documented laptop. That proves bounded prototype scale, not national production scale. Included Neo4j, PostgreSQL, Redis, and Celery seams support the next deployment tier after security and policy approval.

**What is the biggest current limitation?**  
Operation Suraksha is synthetic and the larger supplied validation corpus is not Indian operational data. A real pilot needs authorized, redacted agency exports; jurisdiction-specific evaluation; access and retention controls; and independent security, fairness, and model validation.
