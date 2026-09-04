"""Export the supplied PyTorch GraphSAGE weights for a lightweight web runtime."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch


MODEL_DIR = Path(__file__).resolve().parents[1] / "models"
source = MODEL_DIR / "graphsage_model.pt"
target = MODEL_DIR / "graphsage_numpy_weights.npz"
state = torch.load(source, map_location="cpu", weights_only=True)
np.savez_compressed(target, **{name: value.detach().cpu().numpy() for name, value in state.items()})
print(target.name)
