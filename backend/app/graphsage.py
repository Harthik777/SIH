"""GraphSAGE model adapter for suspect-risk inference.

The supplied notebook contains the model architecture and training procedure,
but the serialized ``graphsage_model.pt`` state dictionary was not included.
This adapter therefore exposes an honest feature preview until that checkpoint
is placed in ``backend/models``.  When the checkpoint and optional PyG runtime
are present, the same endpoint automatically switches to real inference.
"""

from __future__ import annotations

import importlib.util
import json
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any

from .models import GraphPayload


MODEL_DIR = Path(__file__).resolve().parent.parent / "models"
CHECKPOINT_PATH = MODEL_DIR / "graphsage_model.pt"
NOTEBOOK_PATH = MODEL_DIR / "GraphSAGE_Model.ipynb"
MODEL_GRAPH_PATH = MODEL_DIR / "crime_kg_nodes_edges.json"
LINK_PREDICTIONS_PATH = MODEL_DIR / "link_predictions.json"
TRAINING_METADATA_PATH = MODEL_DIR / "graphsage_training.json"

NODE_TYPES = ("CASE", "SUSPECT", "CRIME_TYPE", "POLICE_BEAT", "LOCATION", "VEHICLE")
INPUT_FEATURES = 7
HIDDEN_CHANNELS = 32
OUTPUT_CLASSES = 2
SUPPORTED_ENTITY_TYPES = {"event", "person", "crime", "vehicle", "location"}


def _model_type(node_type: str, name: str, tags: list[str]) -> str:
    if node_type == "event":
        return "CASE"
    if node_type == "person":
        return "SUSPECT"
    if node_type == "crime":
        return "CRIME_TYPE"
    if node_type == "vehicle":
        return "VEHICLE"
    if node_type == "location":
        return "POLICE_BEAT" if "police-beat" in tags or name.startswith("Police Beat ") else "LOCATION"
    raise ValueError(f"GraphSAGE does not support node type: {node_type}")


def runtime_available() -> bool:
    return importlib.util.find_spec("torch") is not None and importlib.util.find_spec("torch_geometric") is not None


def model_status() -> dict[str, Any]:
    has_runtime = runtime_available()
    has_checkpoint = CHECKPOINT_PATH.exists()
    if has_checkpoint and has_runtime:
        status, mode = "ready", "graphsage-inference"
        message = "Checkpoint and PyTorch Geometric runtime are available."
    elif not has_checkpoint:
        status, mode = "checkpoint-required", "structural-feature-preview"
        message = "Architecture is integrated; add graphsage_model.pt to enable trained inference."
    else:
        status, mode = "runtime-required", "structural-feature-preview"
        message = "Checkpoint found; install the optional ML requirements to enable inference."

    reproduced_training = json.loads(TRAINING_METADATA_PATH.read_text(encoding="utf-8")) if TRAINING_METADATA_PATH.exists() else None
    return {
        "id": "graphsage-suspect-risk-v1",
        "name": "GraphSAGE Suspect Risk",
        "status": status,
        "mode": mode,
        "message": message,
        "task": "binary suspect classification",
        "architecture": {
            "input_features": INPUT_FEATURES,
            "node_type_features": list(NODE_TYPES),
            "structural_features": ["normalized_degree"],
            "hidden_channels": [HIDDEN_CHANNELS, HIDDEN_CHANNELS],
            "output_classes": ["normal", "suspicious"],
            "dropout": 0.3,
        },
        "training_summary": {
            "nodes": 1530,
            "edges": 2127,
            "suspects": 434,
            "positive_suspects": 61,
            "validation_suspects": 87,
            "reported_final_validation_f1": 1.0,
            "label_rule": "suspicious when connected to at least two case nodes",
            "reproduced_checkpoint": reproduced_training,
        },
        "artifacts": {
            "notebook": NOTEBOOK_PATH.name,
            "model_graph": MODEL_GRAPH_PATH.name,
            "checkpoint": CHECKPOINT_PATH.name,
            "training_metadata": TRAINING_METADATA_PATH.name,
            "checkpoint_available": has_checkpoint,
            "runtime_available": has_runtime,
        },
    }


def build_features(payload: GraphPayload) -> tuple[list[str], list[list[float]], dict[str, int]]:
    """Recreate the notebook's six one-hot features plus normalized degree."""
    node_order = [node.id for node in payload.nodes]
    degree: Counter[str] = Counter()
    for edge in payload.edges:
        degree[edge.source] += 1
        degree[edge.target] += 1
    max_degree = max(degree.values(), default=1)

    features: list[list[float]] = []
    for node in payload.nodes:
        model_type = _model_type(node.type, node.name, node.tags)
        row = [1.0 if model_type == candidate else 0.0 for candidate in NODE_TYPES]
        row.append(degree[node.id] / max_degree)
        features.append(row)
    return node_order, features, dict(degree)


def _case_neighbors(payload: GraphPayload) -> dict[str, int]:
    nodes = {node.id: node for node in payload.nodes}
    counts: dict[str, int] = defaultdict(int)
    for edge in payload.edges:
        source, target = nodes.get(edge.source), nodes.get(edge.target)
        if not source or not target:
            continue
        if source.type == "person" and target.type == "event":
            counts[source.id] += 1
        elif target.type == "person" and source.type == "event":
            counts[target.id] += 1
    return counts


def _preview_items(payload: GraphPayload, limit: int) -> list[dict[str, Any]]:
    node_order, features, degree = build_features(payload)
    feature_by_id = dict(zip(node_order, features, strict=True))
    case_neighbors = _case_neighbors(payload)
    suspects = [node for node in payload.nodes if node.type == "person"]
    suspects.sort(key=lambda node: (-case_neighbors.get(node.id, 0), -node.risk, node.name))
    return [
        {
            "node_id": node.id,
            "name": node.name,
            "case_neighbors": case_neighbors.get(node.id, 0),
            "graph_degree": degree.get(node.id, 0),
            "feature_vector": feature_by_id[node.id],
            "derived_label": "suspicious" if case_neighbors.get(node.id, 0) >= 2 else "normal",
            "probability": None,
            "risk": node.risk,
        }
        for node in suspects[:limit]
    ]


def _schema_safe_preview(payload: GraphPayload, limit: int) -> list[dict[str, Any]]:
    degree: Counter[str] = Counter()
    for edge in payload.edges:
        degree[edge.source] += 1
        degree[edge.target] += 1
    case_neighbors = _case_neighbors(payload)
    suspects = sorted(
        (node for node in payload.nodes if node.type == "person"),
        key=lambda node: (-case_neighbors.get(node.id, 0), -degree[node.id], -node.risk, node.name),
    )
    return [
        {
            "node_id": node.id,
            "name": node.name,
            "case_neighbors": case_neighbors.get(node.id, 0),
            "graph_degree": degree[node.id],
            "feature_vector": [],
            "derived_label": "suspicious" if case_neighbors.get(node.id, 0) >= 2 else "normal",
            "probability": None,
            "risk": node.risk,
        }
        for node in suspects[:limit]
    ]


def create_model() -> Any:
    import torch.nn.functional as functional
    from torch import nn
    from torch_geometric.nn import SAGEConv

    class GraphSAGE(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.sage1 = SAGEConv(INPUT_FEATURES, HIDDEN_CHANNELS)
            self.sage2 = SAGEConv(HIDDEN_CHANNELS, HIDDEN_CHANNELS)
            self.classifier = nn.Linear(HIDDEN_CHANNELS, OUTPUT_CLASSES)

        def forward(self, x: Any, edge_index: Any) -> Any:
            x = functional.relu(self.sage1(x, edge_index))
            x = functional.dropout(x, p=0.3, training=self.training)
            x = functional.relu(self.sage2(x, edge_index))
            return self.classifier(x)

    return GraphSAGE()


def _run_inference(payload: GraphPayload, limit: int) -> list[dict[str, Any]]:
    import torch

    node_order, features, degree = build_features(payload)
    node_index = {node_id: index for index, node_id in enumerate(node_order)}
    edge_pairs: list[list[int]] = []
    for edge in payload.edges:
        if edge.source in node_index and edge.target in node_index:
            source, target = node_index[edge.source], node_index[edge.target]
            edge_pairs.extend(([source, target], [target, source]))

    x = torch.tensor(features, dtype=torch.float32)
    edge_index = torch.tensor(edge_pairs, dtype=torch.long).t().contiguous()
    model = create_model()
    state_dict = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=True)
    model.load_state_dict(state_dict)
    model.eval()
    with torch.no_grad():
        probabilities = torch.softmax(model(x, edge_index), dim=1)[:, 1].tolist()

    case_neighbors = _case_neighbors(payload)
    nodes = {node.id: node for node in payload.nodes}
    items = []
    for node_id, probability in zip(node_order, probabilities, strict=True):
        node = nodes[node_id]
        if node.type != "person":
            continue
        items.append(
            {
                "node_id": node.id,
                "name": node.name,
                "case_neighbors": case_neighbors.get(node.id, 0),
                "graph_degree": degree.get(node.id, 0),
                "feature_vector": features[node_index[node.id]],
                "derived_label": "suspicious" if probability >= 0.5 else "normal",
                "probability": round(float(probability), 6),
                "risk": node.risk,
            }
        )
    items.sort(key=lambda item: (-item["probability"], -item["risk"], item["name"]))
    return items[:limit]


def analyze_graph(payload: GraphPayload, limit: int = 25) -> dict[str, Any]:
    status = model_status()
    mode = status["mode"]
    message = status["message"]
    unsupported = sorted({node.type for node in payload.nodes} - SUPPORTED_ENTITY_TYPES)
    if unsupported:
        mode = "schema-incompatible-preview"
        message = f"GraphSAGE inference withheld: the active graph includes out-of-training-schema node types ({', '.join(unsupported)}). Structural person signals are shown instead."
        review_status = {**status, "status": "schema-review", "mode": mode, "message": message}
        items = _schema_safe_preview(payload, limit)
        return {"model": review_status, "mode": mode, "message": message, "items": items, "count": len(items)}
    if mode == "graphsage-inference":
        try:
            items = _run_inference(payload, limit)
        except Exception as exc:  # A mismatched state dict should not take down analytics.
            mode = "inference-error"
            message = f"GraphSAGE checkpoint could not be loaded: {type(exc).__name__}."
            items = _preview_items(payload, limit)
    else:
        items = _preview_items(payload, limit)
    return {"model": status, "mode": mode, "message": message, "items": items, "count": len(items)}


@lru_cache(maxsize=8)
def _cached_active_analysis(investigation_id: str) -> dict[str, Any]:
    from .investigation_store import get_active_graph

    return analyze_graph(get_active_graph(), 5000)


def analyze_active_graph(limit: int = 25) -> dict[str, Any]:
    """Run once per active investigation, then slice cached CPU inference."""
    from .investigation_store import active_investigation

    result = _cached_active_analysis(active_investigation()["id"])
    items = result["items"][:limit]
    return {**result, "items": items, "count": len(items)}


@lru_cache(maxsize=1)
def load_supplied_link_predictions() -> list[dict[str, Any]]:
    if not LINK_PREDICTIONS_PATH.exists():
        return []
    payload = json.loads(LINK_PREDICTIONS_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Supplied link prediction artifact must contain a JSON list")
    return [item for item in payload if isinstance(item, dict)]


def link_prediction_summary() -> dict[str, Any]:
    rows = load_supplied_link_predictions()
    probabilities = [float(row["link_probability"]) for row in rows if "link_probability" in row]
    predicted = sum(int(row.get("predicted_link", 0)) for row in rows)
    return {
        "artifact": LINK_PREDICTIONS_PATH.name,
        "rows": len(rows),
        "predicted_links": predicted,
        "mean_probability": round(sum(probabilities) / len(probabilities), 4) if probabilities else None,
        "uniform_probability": len({round(value, 8) for value in probabilities}) <= 1,
        "note": "Precomputed link-prediction output supplied separately from the GraphSAGE checkpoint.",
    }
