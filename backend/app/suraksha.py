"""Flagship, fully synthetic multi-source investigation and evaluation harness."""

from __future__ import annotations

import hashlib
import json
import threading
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from .crime_pipeline import build_multisource_graph
from .models import GraphPayload
from .trace_engine import connection_path


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SURAKSHA_PATH = DATA_DIR / "operation_suraksha.json"
GROUND_TRUTH_PATH = DATA_DIR / "operation_suraksha_ground_truth.json"
DECISIONS_PATH = DATA_DIR / "investigations" / "suraksha_resolution_decisions.json"
SURAKSHA_ID = "operation-suraksha"
_LOCK = threading.RLock()


def _canonical_receipt(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@lru_cache(maxsize=1)
def load_suraksha_records() -> list[dict[str, str]]:
    payload = json.loads(SURAKSHA_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise ValueError("Operation Suraksha must contain a JSON record list")
    return [{str(key): "" if value is None else str(value) for key, value in item.items()} for item in payload]


@lru_cache(maxsize=1)
def load_suraksha_graph() -> GraphPayload:
    return build_multisource_graph(load_suraksha_records())


@lru_cache(maxsize=1)
def ground_truth() -> dict[str, Any]:
    return json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))


def source_counts() -> dict[str, int]:
    def source_kind(row: dict[str, str]) -> str:
        if row.get("call_id"):
            return "CDR"
        if row.get("transaction_id"):
            return "BANK"
        identifier = row.get("record_id", "")
        if identifier.startswith("FIR-"):
            return "FIR"
        if identifier.startswith("ANPR-"):
            return "ANPR"
        if identifier.startswith("SURV-"):
            return "SURVEILLANCE"
        if row.get("post_id"):
            return "OSINT"
        return "OTHER"

    return dict(sorted(Counter(source_kind(row) for row in load_suraksha_records()).items()))


def _node_by_name(payload: GraphPayload, name: str):
    return next((node for node in payload.nodes if node.name == name), None)


def evaluation() -> dict[str, Any]:
    payload = load_suraksha_graph()
    truth = ground_truth()
    names = {node.name for node in payload.nodes}
    relationship_types = {edge.label for edge in payload.edges}
    entity_checks = [{"name": name, "recovered": name in names} for name in truth["required_entities"]]
    relationship_checks = [{"relationship": label, "recovered": label in relationship_types} for label in truth["required_relationship_types"]]
    source = _node_by_name(payload, truth["expected_path"]["source"])
    target = _node_by_name(payload, truth["expected_path"]["target"])
    path = connection_path(payload, source.id, target.id, truth["expected_path"]["maximum_hops"]) if source and target else {"found": False, "receipt": None}
    negative = truth["negative_identity_control"]
    left, right = _node_by_name(payload, negative["left"]), _node_by_name(payload, negative["right"])
    distinct_identity_nodes = bool(left and right and left.id != right.id)
    summary = {
        "entities_recovered": sum(item["recovered"] for item in entity_checks),
        "entities_expected": len(entity_checks),
        "relationships_recovered": sum(item["recovered"] for item in relationship_checks),
        "relationships_expected": len(relationship_checks),
        "hidden_path_recovered": bool(path["found"]),
        "false_merges": 0 if distinct_identity_nodes else 1,
        "processing_mode": "deterministic-local",
    }
    result = {
        "investigation_id": SURAKSHA_ID,
        "classification": truth["classification"],
        "summary": summary,
        "entity_checks": entity_checks,
        "relationship_checks": relationship_checks,
        "expected_path": {
            "source": truth["expected_path"]["source"],
            "target": truth["expected_path"]["target"],
            "found": bool(path["found"]),
            "hops": path.get("hops"),
            "trace_receipt": path.get("receipt"),
        },
        "negative_identity_control": {
            **negative,
            "distinct_nodes_preserved": distinct_identity_nodes,
        },
        "scope_note": "Scenario acceptance checks on synthetic ground truth; not an independent real-world accuracy claim.",
    }
    return {**result, "receipt": _canonical_receipt(result)}


def replay() -> dict[str, Any]:
    payload = load_suraksha_graph()

    def evidence(*identifiers: str) -> list[str]:
        return [node.id for node in payload.nodes if any(identifier in node.name for identifier in identifiers)]

    steps = [
        {
            "order": 1,
            "time": "18 Aug · 19:10",
            "source": "FIR",
            "title": "First complaint establishes identifiers",
            "finding": "A fictional complaint records Subject A-17, a phone, a vehicle, an organization, and Majestic Transit Hub.",
            "evidence_ids": evidence("FIR-S-001"),
            "status": "observation",
        },
        {
            "order": 2,
            "time": "18 Aug · 18:48–19:02",
            "source": "CDR",
            "title": "Pre-incident communication burst",
            "finding": "Three synthetic CDRs connect the three coded subjects through recorded phone identifiers before the complaint time.",
            "evidence_ids": evidence("CALL-S-001", "CALL-S-002", "CALL-S-003"),
            "status": "derived-lead",
        },
        {
            "order": 3,
            "time": "18–19 Aug",
            "source": "BANK",
            "title": "Circular transaction path appears",
            "finding": "Recorded transfers form AC-SUR-1101 → AC-SUR-2201 → AC-SUR-3301 → AC-SUR-1101. The cycle is a review signal, not proof of unlawful purpose.",
            "evidence_ids": evidence("TX-S-001", "TX-S-003", "TX-S-004"),
            "status": "derived-lead",
        },
        {
            "order": 4,
            "time": "20 Aug · 20:31–20:49",
            "source": "ANPR + CDR + SURVEILLANCE",
            "title": "Independent sources converge at Majestic",
            "finding": "A vehicle observation, tower records, and a surveillance record share a narrow synthetic time window and location.",
            "evidence_ids": evidence("ANPR-S-002", "CALL-S-005", "CALL-S-006", "SURV-S-002"),
            "status": "derived-lead",
        },
        {
            "order": 5,
            "time": "21 Aug · 17:58–18:42",
            "source": "ANPR + FIR + OSINT",
            "title": "Coordinator becomes the bridge entity",
            "finding": "Coordinator C-04 connects communications, accounts, the shared vehicle, the organization, and later complaint records.",
            "evidence_ids": evidence("ANPR-S-003", "FIR-S-004", "OSINT-S-002"),
            "status": "derived-lead",
        },
        {
            "order": 6,
            "time": "24 Aug · 10:00–10:02",
            "source": "IDENTITY CONTROL",
            "title": "False merge is deliberately prevented",
            "finding": "Kavya Rao and K. Rao remain separate because distinct phones and near-simultaneous observations in different cities contradict a name-only merge.",
            "evidence_ids": evidence("CALL-S-009", "CALL-S-010"),
            "status": "human-review",
        },
    ]
    signed_steps = [{**step, "receipt": _canonical_receipt(step)} for step in steps]
    result = {
        "investigation_id": SURAKSHA_ID,
        "title": "Operation Suraksha",
        "subtitle": "Synthetic multi-source evidence-fusion exercise",
        "classification": "SYNTHETIC · NO REAL PERSON OR CASE DATA",
        "source_counts": source_counts(),
        "records": len(load_suraksha_records()),
        "nodes": len(payload.nodes),
        "edges": len(payload.edges),
        "steps": signed_steps,
        "guardrail": "The replay explains recorded and derived connections. It does not determine identity, intent, culpability, or enforcement action.",
    }
    return {**result, "receipt": _canonical_receipt(result)}


def _read_decisions() -> dict[str, Any]:
    if not DECISIONS_PATH.exists():
        return {}
    try:
        value = json.loads(DECISIONS_PATH.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def resolution_candidates() -> list[dict[str, Any]]:
    payload = load_suraksha_graph()
    left = _node_by_name(payload, "Kavya Rao")
    right = _node_by_name(payload, "K. Rao")
    if not left or not right:
        return []
    decision = _read_decisions().get("suraksha-identity-kr")
    candidate = {
        "id": "suraksha-identity-kr",
        "left": left.model_dump(),
        "right": right.model_dump(),
        "similarity": 0.38,
        "supporting_signals": ["Similar abbreviated name", "Both appear in records linked to Community Support Desk"],
        "conflicting_signals": ["Distinct phone identifiers", "Near-simultaneous observations in Bengaluru and Mysuru", "No shared immutable identifier"],
        "recommendation": "keep-separate",
        "status": decision["decision"] if decision else "pending-review",
        "decision": decision,
        "guardrail": "Name similarity alone is insufficient to merge identities.",
    }
    return [{**candidate, "receipt": _canonical_receipt(candidate)}]


def record_resolution_decision(
    candidate_id: str,
    decision: Literal["keep-separate", "escalate"],
    rationale: str,
) -> dict[str, Any]:
    candidate = next((item for item in resolution_candidates() if item["id"] == candidate_id), None)
    if candidate is None:
        raise KeyError(candidate_id)
    value = {
        "decision": decision,
        "rationale": rationale.strip(),
        "effect": "Identity nodes remain separate" if decision == "keep-separate" else "Queued for additional source verification",
    }
    with _LOCK:
        decisions = _read_decisions()
        decisions[candidate_id] = value
        DECISIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
        temporary = DECISIONS_PATH.with_suffix(".tmp")
        temporary.write_text(json.dumps(decisions, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        temporary.replace(DECISIONS_PATH)
    return {**value, "receipt": _canonical_receipt({"candidate_id": candidate_id, **value})}


def source_sha256() -> str:
    return _file_sha256(SURAKSHA_PATH)
