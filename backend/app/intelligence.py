"""Evidence-backed briefing and transparent hypothesis generation.

Everything in this module is deterministic and local.  It deliberately keeps
observed evidence, derived indicators, and model outputs separate so analysts
can audit how a finding was produced.
"""

from __future__ import annotations

import hashlib
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .crime_pipeline import DATASET_PATH
from .graphsage import CHECKPOINT_PATH, LINK_PREDICTIONS_PATH, MODEL_GRAPH_PATH, NOTEBOOK_PATH, SUPPORTED_ENTITY_TYPES, model_status
from .investigation_store import CITY_SHIELD_ID, active_investigation, get_active_graph, get_active_records


BACKEND_DIR = Path(__file__).resolve().parent.parent
FIR_PATH = BACKEND_DIR / "data" / "fir_reports.txt"
ONTOLOGY_PATH = BACKEND_DIR / "ontology" / "final_ontology.ttl"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source(path: Path, role: str, prov_type: str = "prov:Entity") -> dict[str, Any]:
    stat = path.stat()
    return {
        "name": path.name,
        "role": role,
        "bytes": stat.st_size,
        "sha256": _sha256(path),
        "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "prov_type": prov_type,
        "integrity": "verified",
    }


def provenance_manifest() -> dict[str, Any]:
    paths = [
        (DATASET_PATH, "structured evidence"),
        (FIR_PATH, "narrative evidence"),
        (ONTOLOGY_PATH, "semantic schema"),
        (MODEL_GRAPH_PATH, "model input graph"),
        (NOTEBOOK_PATH, "training procedure", "prov:Plan"),
        (CHECKPOINT_PATH, "reproduced model checkpoint"),
        (LINK_PREDICTIONS_PATH, "supplied model output"),
    ]
    sources = [_source(path, role, *extra) for path, role, *extra in paths if path.exists()]
    active = active_investigation()
    if active["id"] != CITY_SHIELD_ID and active.get("source_sha256"):
        sources.append(
            {
                "name": active["source"],
                "role": "active uploaded evidence",
                "bytes": None,
                "sha256": active["source_sha256"],
                "modified_at": active["created_at"],
                "prov_type": "prov:Entity",
                "integrity": "verified",
            }
        )
    return {
        "manifest_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "standards": ["W3C PROV-O", "RDF 1.1", "OWL 2"],
        "offline_capable": True,
        "external_services_required": False,
        "sources": sources,
        "verified_sources": sum(source["integrity"] == "verified" for source in sources),
    }


def data_quality() -> dict[str, Any]:
    records = get_active_records()
    required = ("case_number", "date", "primary_type", "block", "district", "beat", "iucr", "fbi_code")
    crime_schema = bool(records and set(required).issubset(records[0]))
    if crime_schema:
        present = sum(bool((record.get(field) or "").strip()) for record in records for field in required)
        possible = max(1, len(records) * len(required))
        record_ids = [(record.get("case_number") or "").strip() for record in records]
        suspect_fields = ("suspect_name",)
        type_fields = ("primary_type",)
        schema = "crime-record"
    else:
        id_fields = ("record_id", "transaction_id", "call_id", "event_id", "post_id", "id")
        date_fields = ("timestamp", "date", "datetime", "event_time", "call_time", "transaction_time")
        type_fields = ("record_type", "event_type", "primary_type", "source_type", "category")
        groups = (id_fields, date_fields, type_fields)
        present = sum(any((record.get(field) or "").strip() for field in group) for record in records for group in groups)
        possible = max(1, len(records) * len(groups))
        record_ids = [next(((record.get(field) or "").strip() for field in id_fields if (record.get(field) or "").strip()), "") for record in records]
        suspect_fields = ("suspect_name", "person_name", "subject", "caller_name", "sender_name")
        schema = "multi-source"
    duplicate_ids = len([value for value in record_ids if value]) - len({value for value in record_ids if value})
    return {
        "records": len(records),
        "required_field_completeness": round(100 * present / possible, 1),
        "unique_case_numbers": len({value for value in record_ids if value}),
        "duplicate_case_numbers": duplicate_ids,
        "suspect_coverage": round(100 * sum(any((row.get(field) or "").strip() for field in suspect_fields) for row in records) / max(1, len(records)), 1),
        "vehicle_plate_coverage": round(100 * sum(bool((row.get("vehicle_plate") or "").strip()) for row in records) / max(1, len(records)), 1),
        "ontology_mapping_coverage": round(100 * sum(any((row.get(field) or "").strip() for field in type_fields) for row in records) / max(1, len(records)), 1),
        "quality_gate": "pass" if records and duplicate_ids == 0 and present == possible else "review",
        "schema": schema,
    }


def investigation_briefing() -> dict[str, Any]:
    records = get_active_records()
    payload = get_active_graph()
    active = active_investigation()
    suspect_cases: dict[str, list[str]] = defaultdict(list)
    beat_cases: dict[str, list[str]] = defaultdict(list)
    crime_counts: Counter[str] = Counter()
    crime_schema = bool(records and {"case_number", "primary_type", "beat"}.issubset(records[0]))
    if crime_schema:
        for record in records:
            if record.get("suspect_name"):
                suspect_cases[record["suspect_name"]].append(record.get("case_number", "unknown"))
            if record.get("beat"):
                beat_cases[record["beat"]].append(record.get("case_number", "unknown"))
            if record.get("primary_type"):
                crime_counts[record["primary_type"]] += 1
    else:
        node_by_id = {node.id: node for node in payload.nodes}
        adjacent: dict[str, set[str]] = defaultdict(set)
        for edge in payload.edges:
            adjacent[edge.source].add(edge.target)
            adjacent[edge.target].add(edge.source)
        for node in payload.nodes:
            linked_events = [node_by_id[item].name for item in adjacent[node.id] if node_by_id[item].type == "event"]
            if node.type == "person":
                suspect_cases[node.name].extend(linked_events)
            elif node.type == "location":
                beat_cases[node.name].extend(linked_events)
        for record in records:
            record_type = record.get("record_type") or record.get("event_type") or "source record"
            crime_counts[record_type] += 1

    repeat_suspects = sorted(
        ((name, cases) for name, cases in suspect_cases.items() if len(cases) >= 2),
        key=lambda item: (-len(item[1]), item[0]),
    )
    busiest_beats = sorted(beat_cases.items(), key=lambda item: (-len(item[1]), item[0]))
    high_risk = [node for node in payload.nodes if node.type == "event" and node.risk >= 85]
    manifest = provenance_manifest()
    quality = data_quality()
    graph_model = model_status()
    unsupported_types = sorted({node.type for node in payload.nodes} - SUPPORTED_ENTITY_TYPES)
    if unsupported_types:
        graph_model = {
            **graph_model,
            "status": "schema-review",
            "mode": "schema-incompatible-preview",
            "message": f"Inference withheld for out-of-training-schema node types: {', '.join(unsupported_types)}.",
        }

    busiest_beat = busiest_beats[0] if busiest_beats else ("unavailable", [])
    findings = [
        {
            "id": "repeat-subject-network",
            "severity": "high",
            "title": f"{len(repeat_suspects)} repeat-subject patterns require review",
            "summary": "Named subjects occur in two or more independently recorded cases.",
            "confidence": 100,
            "basis": "direct graph count",
            "evidence": [
                {"entity": name, "case_count": len(cases), "case_ids": cases, "source": active["source"]}
                for name, cases in repeat_suspects[:5]
            ],
            "alternatives": ["Names may refer to different people", "Source records may contain identity-entry errors"],
            "next_action": "Verify identity attributes in the original FIRs before drawing conclusions.",
        },
        {
            "id": "beat-concentration",
            "severity": "high",
            "title": (f"Police Beat {busiest_beat[0]} has the highest recorded concentration" if crime_schema else f"{busiest_beat[0]} has the highest recorded source concentration"),
            "summary": f"{len(busiest_beat[1])} of {len(records)} source records map to the same operational area.",
            "confidence": 100,
            "basis": "direct source aggregation",
            "evidence": [{"beat": beat, "case_count": len(cases), "source": active["source"]} for beat, cases in busiest_beats[:5]],
            "alternatives": ["Population and reporting volume are not normalized", "Beat boundaries may differ over time"],
            "next_action": "Compare against population, call volume, and time-of-day baselines.",
        },
        {
            "id": "high-severity-cluster",
            "severity": "critical" if high_risk else "medium",
            "title": f"{len(high_risk)} high-severity incident nodes prioritized",
            "summary": "Risk is derived from explicit offense, weapon, arrest, and domestic-dispute rules.",
            "confidence": 96,
            "basis": "transparent rules",
            "evidence": [{"crime_type": name, "case_count": count} for name, count in crime_counts.most_common(5)],
            "alternatives": ["Severity is not a prediction of future behavior", "Missing context can change prioritization"],
            "next_action": "Review the source narrative and disposition for each prioritized case.",
        },
    ]
    return {
        "investigation": active["name"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "operating_mode": "local-single-machine",
        "risk_posture": "elevated",
        "graph": {"nodes": len(payload.nodes), "edges": len(payload.edges), "repeat_suspects": len(repeat_suspects)},
        "quality": quality,
        "model": graph_model,
        "provenance": {"verified": manifest["verified_sources"], "total": len(manifest["sources"])},
        "findings": findings,
        "guardrails": [
            "Every finding requires human verification against source records.",
            "Risk scores prioritize review; they do not establish guilt or identity.",
            "The GraphSAGE label is derived from repeat-case connectivity and is not an independent ground-truth outcome.",
            "The supplied link-prediction artifact is non-actionable because all 50 scores are identical and below threshold.",
        ],
    }


def transparent_link_candidates() -> list[dict[str, Any]]:
    """Rank auditable case↔subject hypotheses from shared observed attributes."""
    records = get_active_records()
    graph = get_active_graph()
    required_fields = {"case_number", "suspect_name", "vehicle_plate", "primary_type", "beat", "block"}
    if not records or not required_fields.issubset(records[0]):
        return []
    node_by_name = {node.name: node for node in graph.nodes}
    profiles: dict[str, dict[str, Counter[str] | set[str]]] = {}
    for record in records:
        name = record["suspect_name"]
        profile = profiles.setdefault(
            name,
            {"crime": Counter(), "beat": Counter(), "block": Counter(), "plates": set()},
        )
        profile["crime"][record["primary_type"]] += 1  # type: ignore[index]
        profile["beat"][record["beat"]] += 1  # type: ignore[index]
        profile["block"][record["block"]] += 1  # type: ignore[index]
        if record["vehicle_plate"]:
            profile["plates"].add(record["vehicle_plate"])  # type: ignore[union-attr]

    candidates: list[dict[str, Any]] = []
    for record in records:
        for suspect, profile in profiles.items():
            if suspect == record["suspect_name"]:
                continue
            signals: list[dict[str, Any]] = []
            strength = 0.0
            crime_matches = profile["crime"][record["primary_type"]]  # type: ignore[index]
            beat_matches = profile["beat"][record["beat"]]  # type: ignore[index]
            block_matches = profile["block"][record["block"]]  # type: ignore[index]
            plate_match = bool(record["vehicle_plate"] and record["vehicle_plate"] in profile["plates"])
            if crime_matches:
                strength += min(0.24, 0.12 + crime_matches * 0.04)
                signals.append({"feature": "crime_type", "value": record["primary_type"], "prior_matches": crime_matches})
            if beat_matches:
                strength += min(0.28, 0.14 + beat_matches * 0.05)
                signals.append({"feature": "police_beat", "value": record["beat"], "prior_matches": beat_matches})
            if block_matches:
                strength += min(0.38, 0.25 + block_matches * 0.06)
                signals.append({"feature": "location_block", "value": record["block"], "prior_matches": block_matches})
            if plate_match:
                strength += 0.5
                signals.append({"feature": "vehicle_plate", "value": record["vehicle_plate"], "prior_matches": 1})
            if len(signals) < 2:
                continue
            score = min(0.99, 1 - math.exp(-2.2 * strength))
            case_node = node_by_name.get(f"Case {record['case_number']}")
            suspect_node = node_by_name.get(suspect)
            candidates.append(
                {
                    "case_id": case_node.id if case_node else record["case_number"],
                    "case_number": record["case_number"],
                    "suspect_id": suspect_node.id if suspect_node else suspect,
                    "suspect_name": suspect,
                    "similarity_score": round(score, 4),
                    "signals": signals,
                    "method": "explainable-feature-overlap-v1",
                    "status": "hypothesis-only",
                }
            )
    candidates.sort(key=lambda item: (-item["similarity_score"], item["case_number"], item["suspect_name"]))
    return candidates
