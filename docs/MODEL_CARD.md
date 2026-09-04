# GraphSAGE suspect-prioritization model card

## Intended use

The bundled two-layer GraphSAGE checkpoint ranks suspect nodes for analyst review inside the supplied crime-graph schema. It is a prioritization aid, not evidence of guilt and not an automated enforcement system.

## Inputs and exclusions

- Six one-hot node-type features plus normalized graph degree.
- Undirected message passing over the active compatible evidence graph.
- Protected-person nodes and their incident edges are removed before feature construction and inference.
- Graphs containing node types outside the training schema are refused and shown only as structural previews.

## Evaluation

Run `python backend/scripts/evaluate_model.py` to regenerate `backend/benchmarks/model_evaluation.json`. The artifact reports confusion matrices, precision, recall, F1, accuracy, Brier score and two fixed transparent baselines.

The positive label means “connected to at least two case nodes.” It is a structural proxy generated from the same graph—not an independently adjudicated criminal-outcome label. Consequently, the reproduced validation score demonstrates checkpoint reproducibility, not real-world generalization.

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
