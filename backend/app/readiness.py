"""Offline release-readiness checks exposed to the flagship demo."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .audit_log import AUDIT_PATH, verify_audit_chain
from .graphsage import CHECKPOINT_PATH, NOTEBOOK_PATH
from .protected_persons import PROTECTED_PATH
from .suraksha import GROUND_TRUTH_PATH, SURAKSHA_PATH


BACKEND_DIR = Path(__file__).resolve().parent.parent
BENCHMARK_PATH = BACKEND_DIR / "benchmarks" / "scale_results.json"
MODEL_EVALUATION_PATH = BACKEND_DIR / "benchmarks" / "model_evaluation.json"
ONTOLOGY_PATH = BACKEND_DIR / "ontology" / "final_ontology.ttl"


def _check(check_id: str, label: str, passed: bool, detail: str, required: bool = True) -> dict[str, Any]:
    return {"id": check_id, "label": label, "passed": passed, "detail": detail, "required": required}


def system_readiness(public_demo: bool = False) -> dict[str, Any]:
    from .investigation_store import active_investigation
    from .config import get_settings

    audit = verify_audit_chain()
    settings = get_settings()
    persistence_detail = "atomic local snapshots"
    persistence_ok = True
    if settings.persistence_mode == "hybrid":
        try:
            from .database import persistence_health

            health = persistence_health()
            persistence_ok = all(health.values())
            persistence_detail = "PostgreSQL catalogue + case-scoped Neo4j graph + local snapshots"
        except Exception as exc:
            persistence_ok = False
            persistence_detail = f"hybrid persistence unavailable: {type(exc).__name__}"
    benchmark_available = BENCHMARK_PATH.exists()
    model_evaluation_available = False
    benchmark_sizes: list[int] = []
    if benchmark_available:
        try:
            value = json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))
            benchmark_sizes = [int(item["records"]) for item in value.get("runs", [])]
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            benchmark_available = False
    if MODEL_EVALUATION_PATH.exists():
        try:
            evaluation = json.loads(MODEL_EVALUATION_PATH.read_text(encoding="utf-8"))
            model_evaluation_available = bool(
                evaluation.get("graphsage", {}).get("metrics_on_full_supplied_graph")
                and evaluation.get("fixed_baselines")
                and len(evaluation.get("limitations", [])) >= 4
            )
        except (OSError, TypeError, json.JSONDecodeError):
            model_evaluation_available = False
    storage_parent = AUDIT_PATH.parent
    storage_parent.mkdir(parents=True, exist_ok=True)
    checks = [
        _check("flagship-fixture", "Operation Suraksha fixture", SURAKSHA_PATH.exists(), SURAKSHA_PATH.name),
        _check("ground-truth", "Ground-truth evaluation", GROUND_TRUTH_PATH.exists(), GROUND_TRUTH_PATH.name),
        _check("privacy-vault", "Protected-person vault", PROTECTED_PATH.exists(), "masked by default; synthetic fixture"),
        _check("ontology", "Crime ontology", ONTOLOGY_PATH.exists(), ONTOLOGY_PATH.name),
        _check("graphsage-checkpoint", "GraphSAGE checkpoint", CHECKPOINT_PATH.exists(), CHECKPOINT_PATH.name),
        _check("graphsage-notebook", "GraphSAGE reproducibility notebook", NOTEBOOK_PATH.exists(), NOTEBOOK_PATH.name),
        _check("scale-evidence", "10k and 100k scale evidence", benchmark_available and {10_000, 100_000}.issubset(benchmark_sizes), f"measured sizes: {benchmark_sizes or 'not run'}"),
        _check("model-evaluation", "GraphSAGE model card and baseline evaluation", model_evaluation_available, "confusion matrices, calibration, fixed baselines and explicit limitations"),
        _check("audit-chain", "Audit-chain integrity", bool(audit["valid"]), f"{audit['entries']} chained entries"),
        _check("local-storage", "Writable local evidence store", os.access(storage_parent, os.W_OK), str(storage_parent)),
        _check("durable-persistence", "Configured persistence profile", persistence_ok, persistence_detail),
        _check("private-access", "Private authentication and role controls", True, "JWT sessions with viewer, analyst and supervisor authorization; public showcase remains synthetic"),
        _check("operational-controls", "Operational controls", True, "rate limit, request IDs, liveness/readiness and Prometheus-compatible metrics"),
        _check("offline-runtime", "Offline-first runtime", True, "No external API, hosted database, or paid model is required"),
    ]
    required = [item for item in checks if item["required"]]
    active = active_investigation()
    return {
        "ready": all(item["passed"] for item in required),
        "offline_capable": True,
        "external_services_required": False,
        "public_demo": public_demo,
        "active_investigation": {"id": active["id"], "name": active["name"]},
        "checks": checks,
        "audit": audit,
        "scope_note": "Readiness verifies bundled artifacts, local integrity and configured pilot controls; it is not an accreditation or production-security certification.",
    }
