"""Generate a reproducible, limitation-aware GraphSAGE evaluation artifact."""

from __future__ import annotations

import json
import math
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.crime_pipeline import load_crime_graph  # noqa: E402
from app.graphsage import analyze_graph  # noqa: E402
from sklearn.model_selection import train_test_split  # noqa: E402


def brier_score(truth: list[int], probabilities: list[float]) -> float | None:
    if not truth or len(truth) != len(probabilities):
        return None
    value = sum((probability - actual) ** 2 for probability, actual in zip(probabilities, truth, strict=True)) / len(truth)
    return round(value, 6) if math.isfinite(value) else None


def classification_metrics(truth: list[int], prediction: list[int]) -> dict[str, float | int]:
    tp = sum(actual == predicted == 1 for actual, predicted in zip(truth, prediction, strict=True))
    tn = sum(actual == predicted == 0 for actual, predicted in zip(truth, prediction, strict=True))
    fp = sum(actual == 0 and predicted == 1 for actual, predicted in zip(truth, prediction, strict=True))
    fn = sum(actual == 1 and predicted == 0 for actual, predicted in zip(truth, prediction, strict=True))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "true_positive": tp,
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "f1": round(f1, 6),
        "accuracy": round((tp + tn) / len(truth), 6),
    }


def main() -> None:
    payload = load_crime_graph()
    result = analyze_graph(payload, 10_000)
    rows = result["items"]
    truth = [1 if row["case_neighbors"] >= 2 else 0 for row in rows]
    model_prediction = [1 if row["derived_label"] == "suspicious" else 0 for row in rows]
    risk_baseline = [1 if row["risk"] >= 70 else 0 for row in rows]
    degree_baseline = [1 if row["graph_degree"] >= 4 else 0 for row in rows]
    probabilities = [float(row["probability"]) for row in rows if row["probability"] is not None]
    brier = brier_score(truth, probabilities)
    by_id = {row["node_id"]: row for row in rows}
    suspect_ids = [node.id for node in payload.nodes if node.type == "person"]
    suspect_truth = [1 if by_id[node_id]["case_neighbors"] >= 2 else 0 for node_id in suspect_ids]
    _, validation_ids = train_test_split(
        suspect_ids,
        test_size=0.2,
        random_state=42,
        stratify=suspect_truth,
    )
    validation_rows = [by_id[node_id] for node_id in validation_ids]
    validation_truth = [1 if row["case_neighbors"] >= 2 else 0 for row in validation_rows]
    validation_prediction = [1 if row["derived_label"] == "suspicious" else 0 for row in validation_rows]
    validation_probabilities = [float(row["probability"]) for row in validation_rows if row["probability"] is not None]
    artifact = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "classification": "supplied-corpus-model-evaluation",
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "dataset": {
            "source": "crime_dataset.csv transformed into crime_kg_nodes_edges.json",
            "suspects": len(rows),
            "positive_suspects": sum(truth),
            "label_definition": "positive when a suspect is connected to at least two case nodes",
        },
        "graphsage": {
            "runtime_mode": result["mode"],
            "threshold": 0.5,
            "metrics_on_full_supplied_graph": classification_metrics(truth, model_prediction),
            "brier_score": brier,
            "reported_reproduced_validation_f1": result["model"]["training_summary"]["reproduced_checkpoint"]["validation_f1"],
            "held_out_node_validation": {
                "samples": len(validation_rows),
                "positive_samples": sum(validation_truth),
                "split_seed": 42,
                "split_type": "fixed stratified transductive node holdout",
                "metrics": classification_metrics(validation_truth, validation_prediction),
                "brier_score": brier_score(validation_truth, validation_probabilities),
                "independent_outcome_labels": False,
            },
        },
        "fixed_baselines": {
            "risk_score_at_least_70": classification_metrics(truth, risk_baseline),
            "graph_degree_at_least_4": classification_metrics(truth, degree_baseline),
        },
        "decision_policy": "Model outputs are prioritization signals; no automated identity, guilt, arrest, or enforcement decision is permitted.",
        "claim_assurance": {
            "field_accuracy": "not-established",
            "operational_use": "prohibited-without-independent-validation",
            "feature_target_dependency": "high",
            "dependency_explanation": "The target is defined from case-neighbor topology while graph topology and normalized degree are model inputs. The metric demonstrates reproducibility of a structural rule, not prediction of criminal conduct.",
            "permitted_claim": "The supplied GraphSAGE notebook and checkpoint are reproducible for structural suspect prioritization on the supplied demonstration graph.",
            "prohibited_claims": [
                "real-world crime prediction accuracy",
                "proof of identity, intent, culpability, or guilt",
                "fairness or generalization across populations, jurisdictions, or time",
            ],
            "release_gate": "Evaluate on independently labelled, temporally separated, legally approved data with subgroup and drift analysis before any operational pilot.",
        },
        "limitations": [
            "The labels are structural proxy labels derived from the same graph, not independently adjudicated criminal outcomes.",
            "The supplied corpus is demonstration data and does not establish field generalization, fairness, or causal validity.",
            "Thresholds were not tuned on the reported full-graph metrics; external labelled evaluation is required before operational use.",
            "Protected-person nodes are excluded from model features and predictions.",
        ],
    }
    destination = BACKEND_DIR / "benchmarks" / "model_evaluation.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(destination.relative_to(PROJECT_DIR))


if __name__ == "__main__":
    main()
