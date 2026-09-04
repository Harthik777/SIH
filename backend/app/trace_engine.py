"""TRACE: proof-carrying, counterfactual graph intelligence.

TRACE keeps a strict boundary between observed graph relationships and derived
investigative leads. Every result includes the evidence path and a deterministic
receipt so another analyst can reproduce exactly what the system evaluated.
"""

from __future__ import annotations

import hashlib
import heapq
import json
from collections import defaultdict
from datetime import datetime
from typing import Any

from .models import GraphEdge, GraphNode, GraphPayload


TRACE_VERSION = "trace-local-v1"


def _receipt(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _indexes(payload: GraphPayload) -> tuple[dict[str, GraphNode], dict[str, list[tuple[str, GraphEdge]]]]:
    nodes = {node.id: node for node in payload.nodes}
    adjacent: dict[str, list[tuple[str, GraphEdge]]] = defaultdict(list)
    for edge in payload.edges:
        if edge.source in nodes and edge.target in nodes:
            adjacent[edge.source].append((edge.target, edge))
            adjacent[edge.target].append((edge.source, edge))
    return nodes, adjacent


def connection_path(payload: GraphPayload, source_id: str, target_id: str, max_hops: int = 8) -> dict[str, Any]:
    nodes, adjacent = _indexes(payload)
    if source_id not in nodes or target_id not in nodes:
        raise KeyError(source_id if source_id not in nodes else target_id)
    if source_id == target_id:
        result = {
            "found": True,
            "source": nodes[source_id].model_dump(),
            "target": nodes[target_id].model_dump(),
            "hops": 0,
            "path_confidence": 100.0,
            "steps": [],
            "method": TRACE_VERSION,
            "epistemic_status": "observed-path",
        }
        return {**result, "receipt": _receipt(result)}

    queue: list[tuple[float, int, str]] = [(0.0, 0, source_id)]
    distance = {source_id: 0.0}
    previous: dict[str, tuple[str, GraphEdge]] = {}
    while queue:
        cost, hops, current = heapq.heappop(queue)
        if current == target_id:
            break
        if hops >= max_hops or cost > distance.get(current, float("inf")):
            continue
        for neighbor, edge in adjacent[current]:
            # Prefer fewer hops and stronger observed links. Confidence never
            # turns a hypothesis into evidence; TRACE traverses stored edges only.
            edge_cost = 1.0 + (100 - edge.confidence) / 100
            candidate = cost + edge_cost
            if candidate < distance.get(neighbor, float("inf")):
                distance[neighbor] = candidate
                previous[neighbor] = (current, edge)
                heapq.heappush(queue, (candidate, hops + 1, neighbor))

    if target_id not in previous:
        result = {
            "found": False,
            "source": nodes[source_id].model_dump(),
            "target": nodes[target_id].model_dump(),
            "hops": None,
            "path_confidence": None,
            "steps": [],
            "method": TRACE_VERSION,
            "epistemic_status": "no-observed-path",
        }
        return {**result, "receipt": _receipt(result)}

    chain: list[tuple[str, str, GraphEdge]] = []
    cursor = target_id
    while cursor != source_id:
        parent, edge = previous[cursor]
        chain.append((parent, cursor, edge))
        cursor = parent
    chain.reverse()
    confidence = 1.0
    steps = []
    for start, end, edge in chain:
        confidence *= edge.confidence / 100
        steps.append(
            {
                "from": nodes[start].model_dump(),
                "relationship": edge.label,
                "to": nodes[end].model_dump(),
                "edge_id": edge.id,
                "confidence": edge.confidence,
                "anomalous": edge.anomalous,
                "direction": "forward" if edge.source == start else "reverse traversal",
                "evidence_status": "stored-observation",
            }
        )
    result = {
        "found": True,
        "source": nodes[source_id].model_dump(),
        "target": nodes[target_id].model_dump(),
        "hops": len(steps),
        "path_confidence": round(confidence * 100, 2),
        "steps": steps,
        "method": TRACE_VERSION,
        "epistemic_status": "observed-path",
        "guardrail": "A graph path shows recorded connectivity, not coordination, intent, or guilt.",
    }
    return {**result, "receipt": _receipt(result)}


def counterfactual(payload: GraphPayload, node_id: str) -> dict[str, Any]:
    nodes, adjacent = _indexes(payload)
    if node_id not in nodes:
        raise KeyError(node_id)
    node = nodes[node_id]
    neighbors = [nodes[neighbor] for neighbor, _ in adjacent[node_id]]
    cases = [neighbor for neighbor in neighbors if neighbor.type == "event"]
    factors: list[dict[str, Any]] = [
        {"factor": "stored risk indicator", "value": node.risk, "basis": "active graph", "kind": "derived"},
        {"factor": "direct evidence links", "value": len(neighbors), "basis": "stored relationships", "kind": "observed"},
    ]
    scenarios: list[dict[str, Any]] = []

    if node.type == "person":
        repeat_bonus = min(12, max(0, len(cases) - 1) * 4)
        factors.append({"factor": "linked incident records", "value": len(cases), "basis": [case.name for case in cases], "kind": "observed"})
        if repeat_bonus:
            scenarios.append(
                {
                    "change": "Identity review determines repeated names belong to different people",
                    "risk_after": max(0, node.risk - repeat_bonus),
                    "delta": -repeat_bonus,
                    "required_verification": "Compare immutable identifiers and original FIR identity attributes.",
                }
            )
    elif node.type == "event":
        description = (node.description or "").upper()
        contributions = [
            ("weapon descriptor removed after source correction", 7, "HANDGUN" in description or "WEAPON" in description),
            ("case disposition updated to arrest made", 4, "open" in (node.tags or [])),
            ("domestic marker removed after source correction", 5, "domestic" in (node.tags or [])),
        ]
        for label, points, applies in contributions:
            if applies:
                factors.append({"factor": label, "value": points, "basis": "transparent risk rule", "kind": "derived"})
                scenarios.append({"change": label, "risk_after": max(0, node.risk - points), "delta": -points, "required_verification": "Verify the corrected field against the source report."})
    elif node.type == "location":
        repeat_bonus = min(10, max(0, len(cases) - 1) * 3)
        if repeat_bonus:
            scenarios.append(
                {
                    "change": "Duplicate incident-location assignments are removed",
                    "risk_after": max(0, node.risk - repeat_bonus),
                    "delta": -repeat_bonus,
                    "required_verification": "Verify addresses, beat boundaries, and duplicate case identifiers.",
                }
            )

    if not scenarios:
        scenarios.append(
            {
                "change": "No score-changing assumption is encoded for this entity type",
                "risk_after": node.risk,
                "delta": 0,
                "required_verification": "Review connected source records before changing prioritization.",
            }
        )
    result = {
        "entity": node.model_dump(),
        "factors": factors,
        "scenarios": scenarios,
        "method": TRACE_VERSION,
        "epistemic_status": "counterfactual-decision-support",
        "guardrail": "Counterfactuals test encoded assumptions; they are not forecasts or evidence.",
    }
    return {**result, "receipt": _receipt(result)}


def temporal_motifs(payload: GraphPayload, limit: int = 25) -> dict[str, Any]:
    nodes, adjacent = _indexes(payload)
    motifs: list[dict[str, Any]] = []

    for person in (node for node in payload.nodes if node.type == "person"):
        cases = [nodes[item] for item, _ in adjacent[person.id] if nodes[item].type == "event"]
        if len(cases) < 2:
            continue
        dated: list[tuple[datetime, GraphNode]] = []
        for case in cases:
            if case.lastSeen:
                try:
                    dated.append((datetime.fromisoformat(case.lastSeen), case))
                except ValueError:
                    pass
        dated.sort(key=lambda item: item[0])
        gaps = [(dated[index][0] - dated[index - 1][0]).days for index in range(1, len(dated))]
        minimum_gap = min(gaps) if gaps else None
        communities = sorted({case.community for case in cases})
        location_ids = sorted(
            {
                neighbor
                for case in cases
                for neighbor, _ in adjacent[case.id]
                if nodes[neighbor].type == "location" and "police-beat" not in (nodes[neighbor].tags or [])
            }
        )
        motif_type = "rapid-repeat" if minimum_gap is not None and minimum_gap <= 90 else "repeat-subject"
        rapid_gap = minimum_gap if minimum_gap is not None else 999
        severity = "critical" if len(cases) >= 3 and rapid_gap <= 30 else "high" if len(cases) >= 3 else "medium"
        motif = {
            "id": f"motif-{person.id}",
            "type": motif_type,
            "severity": severity,
            "title": f"{person.name}: {len(cases)} linked incidents",
            "summary": f"Recorded cases span {len(communities)} graph communit{'y' if len(communities) == 1 else 'ies'} and {len(location_ids)} distinct location node(s).",
            "subject": person.model_dump(),
            "case_ids": [case.id for case in cases],
            "case_names": [case.name for case in cases],
            "location_ids": location_ids,
            "minimum_gap_days": minimum_gap,
            "time_start": dated[0][0].isoformat() if dated else None,
            "time_end": dated[-1][0].isoformat() if dated else None,
            "confidence": min([person.confidence, *(case.confidence for case in cases)]),
            "evidence_status": "derived-from-observed-paths",
            "alternative": "Repeated names can represent different individuals; verify identity before escalation.",
        }
        motifs.append({**motif, "receipt": _receipt(motif)})

    beats = [node for node in payload.nodes if node.type == "location" and "police-beat" in (node.tags or [])]
    if beats:
        top = max(beats, key=lambda node: len([item for item, _ in adjacent[node.id] if nodes[item].type == "event"]))
        cases = [nodes[item] for item, _ in adjacent[top.id] if nodes[item].type == "event"]
        crime_counts: dict[str, int] = defaultdict(int)
        for case in cases:
            for neighbor, _ in adjacent[case.id]:
                if nodes[neighbor].type == "crime":
                    crime_counts[nodes[neighbor].name] += 1
        dominant = max(crime_counts.items(), key=lambda item: item[1]) if crime_counts else ("unknown", 0)
        motif = {
            "id": f"motif-concentration-{top.id}",
            "type": "area-concentration",
            "severity": "high",
            "title": f"{top.name}: {len(cases)} incident concentration",
            "summary": f"{dominant[0]} is the most frequent linked offense type ({dominant[1]} cases).",
            "subject": top.model_dump(),
            "case_ids": [case.id for case in cases],
            "case_names": [case.name for case in cases[:10]],
            "location_ids": [top.id],
            "minimum_gap_days": None,
            "time_start": None,
            "time_end": None,
            "confidence": top.confidence,
            "evidence_status": "derived-from-observed-paths",
            "alternative": "Concentration is not normalized for population, reporting volume, or boundary changes.",
        }
        motifs.append({**motif, "receipt": _receipt(motif)})

    severity_order = {"critical": 3, "high": 2, "medium": 1, "low": 0}
    motifs.sort(key=lambda item: (-severity_order[item["severity"]], -(len(item["case_ids"])), item["title"]))
    result = {
        "method": TRACE_VERSION,
        "epistemic_status": "derived-investigative-leads",
        "guardrail": "Motifs prioritize corroboration. They do not establish identity, coordination, or guilt.",
        "items": motifs[:limit],
        "total": len(motifs),
    }
    return {**result, "receipt": _receipt(result)}


def entity_trace(payload: GraphPayload, node_id: str) -> dict[str, Any]:
    nodes, adjacent = _indexes(payload)
    if node_id not in nodes:
        raise KeyError(node_id)
    node = nodes[node_id]
    neighborhood = []
    for neighbor_id, edge in sorted(adjacent[node_id], key=lambda item: (-item[1].confidence, nodes[item[0]].name)):
        neighborhood.append(
            {
                "edge": edge.model_dump(),
                "neighbor": nodes[neighbor_id].model_dump(),
                "evidence_status": "stored-observation",
            }
        )
    result = {
        "entity": node.model_dump(),
        "neighborhood": neighborhood,
        "counterfactual": counterfactual(payload, node_id),
        "method": TRACE_VERSION,
        "epistemic_status": "proof-carrying-entity-trace",
    }
    return {**result, "receipt": _receipt(result)}
