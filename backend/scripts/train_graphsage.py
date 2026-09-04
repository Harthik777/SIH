"""Reproduce the supplied GraphSAGE notebook and save its state dictionary."""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.crime_pipeline import load_crime_graph  # noqa: E402
from app.graphsage import CHECKPOINT_PATH, TRAINING_METADATA_PATH, build_features, create_model  # noqa: E402


def train(epochs: int = 200, seed: int = 42) -> dict[str, float | int | str]:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    payload = load_crime_graph()
    node_order, features, _ = build_features(payload)
    node_index = {node_id: index for index, node_id in enumerate(node_order)}
    nodes = {node.id: node for node in payload.nodes}

    edge_pairs: list[list[int]] = []
    case_neighbors: dict[str, int] = {node_id: 0 for node_id in node_order}
    for edge in payload.edges:
        source, target = node_index[edge.source], node_index[edge.target]
        edge_pairs.extend(([source, target], [target, source]))
        if nodes[edge.source].type == "person" and nodes[edge.target].type == "event":
            case_neighbors[edge.source] += 1
        elif nodes[edge.target].type == "person" and nodes[edge.source].type == "event":
            case_neighbors[edge.target] += 1

    x = torch.tensor(features, dtype=torch.float32)
    edge_index = torch.tensor(edge_pairs, dtype=torch.long).t().contiguous()
    labels = torch.zeros(len(node_order), dtype=torch.long)
    suspect_indices = [index for index, node_id in enumerate(node_order) if nodes[node_id].type == "person"]
    for index in suspect_indices:
        labels[index] = int(case_neighbors[node_order[index]] >= 2)

    suspect_labels = labels[suspect_indices].numpy()
    train_indices, validation_indices = train_test_split(
        suspect_indices,
        test_size=0.2,
        random_state=42,
        stratify=suspect_labels,
    )
    train_mask = torch.zeros(len(node_order), dtype=torch.bool)
    validation_mask = torch.zeros(len(node_order), dtype=torch.bool)
    train_mask[train_indices] = True
    validation_mask[validation_indices] = True

    model = create_model()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=5e-4)
    loss_function = torch.nn.CrossEntropyLoss(weight=torch.tensor([1.0, 2.0]))
    best_f1 = -1.0
    best_validation_loss = float("inf")
    best_state: dict[str, torch.Tensor] | None = None
    best_epoch = 0

    for epoch in range(1, epochs + 1):
        model.train()
        optimizer.zero_grad()
        output = model(x, edge_index)
        loss = loss_function(output[train_mask], labels[train_mask])
        loss.backward()
        optimizer.step()

        model.eval()
        with torch.no_grad():
            validation_output = model(x, edge_index)
            prediction = validation_output.argmax(dim=1)
            validation_loss = float(loss_function(validation_output[validation_mask], labels[validation_mask]))
        score = f1_score(labels[validation_mask].numpy(), prediction[validation_mask].numpy(), zero_division=0)
        if score > best_f1 or (score == best_f1 and validation_loss < best_validation_loss):
            best_f1 = float(score)
            best_validation_loss = validation_loss
            best_epoch = epoch
            best_state = {name: value.detach().cpu().clone() for name, value in model.state_dict().items()}

    if best_state is None:
        raise RuntimeError("Training did not produce a checkpoint")
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    torch.save(best_state, CHECKPOINT_PATH)
    result: dict[str, float | int | str] = {
        "checkpoint": str(CHECKPOINT_PATH.relative_to(BACKEND_DIR.parent)),
        "epochs": epochs,
        "split_seed": 42,
        "model_seed": seed,
        "best_epoch": best_epoch,
        "validation_f1": round(best_f1, 6),
        "validation_loss": round(best_validation_loss, 6),
        "training_suspects": int(train_mask.sum()),
        "validation_suspects": int(validation_mask.sum()),
    }
    TRAINING_METADATA_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    arguments = parser.parse_args()
    print(train(epochs=arguments.epochs, seed=arguments.seed))
