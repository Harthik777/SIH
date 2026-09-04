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
    brier = sum((probability - actual) ** 2 for probability, actual in zip(probabilities, truth, strict=True)) / len(truth) if len(probabilities) == len(truth) else None
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
            "brier_score": round(brier, 6) if brier is not None and math.isfinite(brier) else None,
            "reported_reproduced_validation_f1": result["model"]["training_summary"]["reproduced_checkpoint"]["validation_f1"],
        },
        "fixed_baselines": {
            "risk_score_at_least_70": classification_metrics(truth, risk_baseline),
            "graph_degree_at_least_4": classification_metrics(truth, degree_baseline),
        },
        "decision_policy": "Model outputs are prioritization signals; no automated identity, guilt, arrest, or enforcement decision is permitted.",
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
