# Independent field-pilot validation protocol

This protocol defines the evidence required before Sentinel can move from a competition pilot to an authorized operational trial. It deliberately contains no real personal data and makes no claim that sponsor validation has already occurred.

## Governance prerequisites

1. Written authorization identifying controller, processor, lawful purpose, retention period and permitted users.
2. Redacted or pseudonymized evaluation exports supplied through an approved channel.
3. Named supervisor for protected-person access and incident response.
4. Approved test environment with encryption, identity federation, malware scanning, backups and deletion procedures.
5. Signed evaluation plan fixing metrics and thresholds before results are inspected.

## Evaluation design

- Use temporally separated cases: training/tuning precedes the test window.
- Keep people and cases disjoint where the objective is inductive generalization.
- Have at least two qualified annotators label entities, relations, candidate identity pairs and review-worthy patterns; adjudicate disagreements.
- Preserve a negative-control set rich in common names, shared locations, family accounts, legitimate repeated payments and clock/location uncertainty.
- Compare Sentinel with the existing manual workflow and transparent non-ML baselines.

## Primary measures

| Capability | Required measurement | Safety emphasis |
| --- | --- | --- |
| Entity extraction | Precision, recall and F1 per entity type | Protected-person recall and exposure incidents reported separately |
| Relation extraction | Precision/recall per predicate and source type | Every accepted edge must resolve to an original record |
| Entity resolution | Pair precision/recall, abstention rate, false-merge rate | False merges are critical errors; name-only merges prohibited |
| Pattern prioritization | Precision@5/10, recall on adjudicated patterns, calibration/Brier score | Alternatives and false-positive reasons reviewed by investigators |
| GraphSAGE ranking | Temporal and entity-disjoint performance versus degree/rule baselines | No operational release if the model does not add validated utility |
| Investigator workflow | Median time-to-first-supported-lead, task completion, correction rate, usability score | Measure overreliance and whether users inspect evidence |
| Performance | Ingestion throughput, p50/p95 search/path latency, peak memory, concurrent cases | Test sponsor-sized files and degraded/recovery behavior |

## Subgroup and drift review

- Evaluate false-positive and false-merge rates across legally approved relevant groups; do not invent sensitive attributes.
- Compare source completeness and error rates by jurisdiction, language, input system and time window.
- Monitor feature and graph-structure drift; invalidate model approval when agreed thresholds are crossed.
- Record model/data version, threshold, evidence hash and reviewer disposition for every evaluated output.

## Exit criteria

The sponsor—not the development team—sets numerical acceptance thresholds. Regardless of threshold, the pilot must have zero unlogged protected-person reveals, zero automated enforcement actions, verifiable source provenance on accepted findings, successful restore testing, and documented handling of every critical security finding.

## Deliverables

- Frozen, hashed evaluation manifest and data dictionary
- Annotator guide and inter-annotator agreement
- Per-source and per-entity metrics with confidence intervals
- False-positive/false-merge case review
- Baseline and ablation comparison
- Privacy, security, usability and performance reports
- Signed go/no-go decision with remaining limitations

