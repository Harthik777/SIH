"""Generate a reproducible, limitation-aware GraphSAGE evaluation artifact."""

from __future__ import annotations

import json
import math
import platform
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.crime_pipeline import load_crime_graph  # noqa: E402
from app.graphsage import analyze_graph  # noqa: E402
from app.models import GraphPayload  # noqa: E402
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


def evidence_masking_stress_test(
    payload: GraphPayload,
    truth_by_id: dict[str, int],
    *,
    mask_rate: float = 0.2,
    trials: int = 10,
    first_seed: int = 1000,
) -> dict[str, object]:
    """Measure sensitivity when a fixed share of person-case evidence is unavailable.

    This deliberately is not called a validation split: the checkpoint has already
    seen the supplied graph.  The test only quantifies robustness to missing source
    evidence while retaining the complete-graph structural proxy as the reference.
    """
    nodes = {node.id: node for node in payload.nodes}
    case_edge_indices = [
        index
        for index, edge in enumerate(payload.edges)
        if {nodes[edge.source].type, nodes[edge.target].type} == {"person", "event"}
    ]
    masked_count = round(len(case_edge_indices) * mask_rate)
    node_ids = list(truth_by_id)
    trial_results: list[dict[str, object]] = []
    for offset in range(trials):
        seed = first_seed + offset
        removed_indices = set(random.Random(seed).sample(case_edge_indices, masked_count))
        masked_payload = GraphPayload(
            nodes=payload.nodes,
            edges=[edge for index, edge in enumerate(payload.edges) if index not in removed_indices],
        )
        masked_result = analyze_graph(masked_payload, 10_000)
        prediction_by_id = {
            row["node_id"]: int(row["derived_label"] == "suspicious")
            for row in masked_result["items"]
        }
        probability_by_id = {row["node_id"]: row["probability"] for row in masked_result["items"]}
        truth = [truth_by_id[node_id] for node_id in node_ids]
        prediction = [prediction_by_id[node_id] for node_id in node_ids]
        probabilities = [probability_by_id[node_id] for node_id in node_ids]
        trial_results.append(
            {
                "seed": seed,
                "masked_case_edges": masked_count,
                "runtime_mode": masked_result["mode"],
                "metrics": classification_metrics(truth, prediction),
                "brier_score": brier_score(truth, probabilities) if all(value is not None for value in probabilities) else None,
            }
        )

    metric_names = ("precision", "recall", "f1", "accuracy")
    summary = {
        metric: {
            "mean": round(mean(float(trial["metrics"][metric]) for trial in trial_results), 6),
            "min": round(min(float(trial["metrics"][metric]) for trial in trial_results), 6),
            "max": round(max(float(trial["metrics"][metric]) for trial in trial_results), 6),
        }
        for metric in metric_names
    }
    brier_values = [float(trial["brier_score"]) for trial in trial_results if trial["brier_score"] is not None]
    return {
        "purpose": "diagnostic robustness to incomplete case-link evidence; not field validation",
        "reference_target": "complete supplied-graph structural proxy",
        "masking_unit": "person-event evidence edges",
        "mask_rate": mask_rate,
        "case_edges": len(case_edge_indices),
        "masked_case_edges_per_trial": masked_count,
        "trials": trials,
        "seed_range": [first_seed, first_seed + trials - 1],
        "summary": summary,
        "brier_score": {
            "mean": round(mean(brier_values), 6),
            "min": round(min(brier_values), 6),
            "max": round(max(brier_values), 6),
        } if brier_values else None,
        "trial_results": trial_results,
        "independent_outcome_labels": False,
        "generalization_claim_allowed": False,
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
    truth_by_id = {row["node_id"]: int(row["case_neighbors"] >= 2) for row in rows}
    stress_test = evidence_masking_stress_test(payload, truth_by_id)
    artifact = {
        "schema_version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "classification": "supplied-corpus-diagnostic-evaluation",
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
            "reproduction_diagnostic": {
                "role": "checkpoint reproduction only; not an independent performance estimate",
                "full_supplied_graph": {
                    "metrics": classification_metrics(truth, model_prediction),
                    "brier_score": brier,
                },
                "checkpoint_selection_partition": {
                    "samples": len(validation_rows),
                    "positive_samples": sum(validation_truth),
                    "split_seed": 42,
                    "split_type": "fixed stratified transductive node partition",
                    "metrics": classification_metrics(validation_truth, validation_prediction),
                    "brier_score": brier_score(validation_truth, validation_probabilities),
                    "independent_outcome_labels": False,
                    "used_for_checkpoint_selection": True,
                },
                "reported_reproduced_f1": result["model"]["training_summary"]["reproduced_checkpoint"]["reproduction_f1"],
            },
            "evidence_masking_stress_test": stress_test,
        },
        "fixed_baselines": {
            "risk_score_at_least_70": classification_metrics(truth, risk_baseline),
            "graph_degree_at_least_4": classification_metrics(truth, degree_baseline),
        },
        "decision_policy": "Model outputs are prioritization signals; no automated identity, guilt, arrest, or enforcement decision is permitted.",
        "leakage_audit": {
            "status": "fails-independent-generalization-criteria",
            "target_derived_from_input_graph": True,
            "checkpoint_selected_on_reported_partition": True,
            "independent_labels": False,
            "identity_disjoint_test": False,
            "temporal_holdout": False,
            "conclusion": "The perfect reproduction score is expected under the supplied structural label design and is not a valid field-performance headline.",
        },
        "claim_assurance": {
            "field_accuracy": "not-established",
            "operational_use": "prohibited-without-independent-validation",
            "feature_target_dependency": "high",
            "dependency_explanation": "The target is defined from case-neighbor topology while graph topology and normalized degree are model inputs. The metric demonstrates reproducibility of a structural rule, not prediction of criminal conduct.",
            "permitted_claim": "The supplied checkpoint is reproducible, and its sensitivity to deliberately masked case-link evidence is measured on the demonstration graph.",
            "prohibited_claims": [
                "real-world crime prediction accuracy",
                "proof of identity, intent, culpability, or guilt",
                "fairness or generalization across populations, jurisdictions, or time",
            ],
            "release_gate": "Evaluate on independently labelled, temporally separated, legally approved data with subgroup and drift analysis before any operational pilot.",
        },
        "limitations": [
            "The labels are structural proxy labels derived from the same graph, not independently adjudicated criminal outcomes.",
            "The original validation partition was used to select the reproduced checkpoint, so its perfect F1 is a reproduction diagnostic rather than an unbiased performance estimate.",
            "The supplied corpus is demonstration data and does not establish field generalization, fairness, or causal validity.",
            "The evidence-masking experiment is a robustness stress test against the complete-graph proxy, not an independent test set.",
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
