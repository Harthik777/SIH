# GraphSAGE suspect-prioritization model card

## Intended use

The bundled two-layer GraphSAGE checkpoint ranks suspect nodes for analyst review inside the supplied crime-graph schema. It is a prioritization aid, not evidence of guilt and not an automated enforcement system.

## Inputs and exclusions

- Six one-hot node-type features plus normalized graph degree.
- Undirected message passing over the active compatible evidence graph.
- Protected-person nodes and their incident edges are removed before feature construction and inference.
- Graphs containing node types outside the training schema are refused and shown only as structural previews.

## Evaluation

Run `python backend/scripts/evaluate_model.py` to regenerate `backend/benchmarks/model_evaluation.json`. The version-2 artifact contains three deliberately separated layers:

1. A **leakage audit** records that the target comes from input-graph topology, the reported partition selected the checkpoint, labels are not independent, and no temporal or identity-disjoint test exists.
2. A **reproduction diagnostic** preserves the supplied notebook/checkpoint result for provenance, not as an unbiased accuracy estimate.
3. A **missing-evidence stress test** masks 20% of person-case links over ten fixed seeds and measures sensitivity against the complete-graph structural proxy. The current mean proxy F1 is `0.825` (range `0.780–0.849`), with mean Brier score `0.103`.

The positive label means “connected to at least two case nodes.” It is a structural proxy generated from the same graph—not an independently adjudicated criminal-outcome label. Graph topology and normalized degree are also model inputs, so the feature/target dependency is explicitly rated **high**. The original perfect result is further biased by checkpoint selection on the reported partition. Consequently, it demonstrates checkpoint reproducibility for this structural rule, not real-world crime prediction or generalization. The masking test is a robustness diagnostic, not a substitute for an external test set.

## Claim passport

- Field accuracy: **not established**.
- Permitted claim: the supplied architecture and reproduced checkpoint can prioritize structural repeat-subject proxies on the supplied graph.
- Prohibited claims: prediction of guilt, intent, identity, real-world crime, fairness, or performance across jurisdictions and time.
- Operational release gate: independently labelled, temporally separated, legally approved evaluation with subgroup, calibration, false-positive, and drift analysis.

## Required safeguards

- A human must verify source evidence and identity before acting.
- Never score victims, survivors, witnesses or other protected people.
- Retain model version, evidence hashes and analyst dispositions in the audit trail.
- Evaluate on representative, legally approved, independently labelled NCRB data before any field pilot.
- Monitor false positives, subgroup performance, calibration and data drift after approval.

## Known limitations

- Demonstration corpus and structural proxy labels.
- No causal claims.
- No fairness claim without appropriate demographic evaluation data and lawful approval.
- The model may reproduce reporting and network-density biases present in source records.
