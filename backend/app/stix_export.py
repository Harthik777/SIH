"""STIX 2.1 case-bundle export for free intelligence interoperability.

The active graph contains criminal-investigation concepts that do not all have
native STIX objects. Standard Identity, Incident, Relationship and Report
objects are used where the semantics match; unstructured places, phones,
accounts and vehicles use a documented ``x-sentinel-entity`` extension instead
of being assigned unsupported STIX semantics.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5

from .models import GraphNode, GraphPayload


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _source_timestamp(value: Any) -> str:
    """Normalize a case creation time so stable STIX IDs keep a stable `created`."""
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    except (TypeError, ValueError):
        return _timestamp()


def _stix_id(object_type: str, investigation_id: str, source_id: str) -> str:
    """Create stable case-scoped identifiers so repeated exports can be diffed."""
    value = uuid5(NAMESPACE_URL, f"sentinel:{investigation_id}:{object_type}:{source_id}")
    return f"{object_type}--{value}"


def _relationship_type(label: str) -> str:
    value = re.sub(r"[^a-z0-9-]+", "-", label.casefold().replace("_", "-")).strip("-")
    return value or "related-to"


def _entity_object(
    node: GraphNode,
    *,
    investigation_id: str,
    created_at: str,
    modified_at: str,
    creator_ref: str,
) -> dict[str, Any]:
    object_type = {
        "person": "identity",
        "protected_person": "identity",
        "organization": "identity",
        "event": "incident",
        "crime": "incident",
    }.get(node.type, "x-sentinel-entity")
    protected = node.type == "protected_person"
    item: dict[str, Any] = {
        "type": object_type,
        "spec_version": "2.1",
        "id": _stix_id(object_type, investigation_id, node.id),
        "created_by_ref": creator_ref,
        "created": created_at,
        "modified": modified_at,
        "name": node.name,
        "confidence": node.confidence,
        "external_references": [{"source_name": "sentinel-active-graph", "external_id": node.id}],
        "x_sentinel_entity_type": node.type,
        "x_sentinel_protected": protected,
    }

    if object_type == "identity":
        item["identity_class"] = "organization" if node.type == "organization" else "individual"

    if protected:
        # The visible graph name is already pseudonymous. Avoid exporting
        # free-text, aliases, place, tags or risk-derived attributes that could
        # enable re-identification or stigmatise a protected person.
        item["description"] = "Protected-person record; identifying and risk-derived attributes suppressed."
        item["x_sentinel_handling"] = "protected-person-masked"
        return item

    item.update(
        {
            "x_sentinel_risk_indicator": node.risk,
            "x_sentinel_risk_interpretation": "derived-review-signal-not-finding",
            "x_sentinel_community": node.community,
        }
    )
    if node.description:
        item["description"] = node.description
    if node.location:
        item["x_sentinel_location_text"] = node.location
    if node.lastSeen:
        item["x_sentinel_last_seen"] = node.lastSeen
    if node.aliases:
        item["x_sentinel_aliases"] = node.aliases
    if node.tags:
        item["x_sentinel_tags"] = node.tags
    return item


def build_stix_bundle(payload: GraphPayload, investigation: dict[str, Any]) -> dict[str, Any]:
    """Return a STIX 2.1 bundle representing the complete active graph."""
    created_at = _source_timestamp(investigation.get("created_at"))
    modified_at = _timestamp()
    investigation_id = str(investigation["id"])
    creator_ref = _stix_id("identity", investigation_id, "sentinel-platform")
    creator = {
        "type": "identity",
        "spec_version": "2.1",
        "id": creator_ref,
        "created": created_at,
        "modified": modified_at,
        "name": "Sentinel Intelligence Platform",
        "identity_class": "system",
        "description": "Source system for this analyst-requested case export.",
    }

    entity_objects = [
        _entity_object(
            node,
            investigation_id=investigation_id,
            created_at=created_at,
            modified_at=modified_at,
            creator_ref=creator_ref,
        )
        for node in payload.nodes
    ]
    refs_by_source_id = {node.id: item["id"] for node, item in zip(payload.nodes, entity_objects, strict=True)}

    relationship_objects: list[dict[str, Any]] = []
    for edge in payload.edges:
        source_ref = refs_by_source_id.get(edge.source)
        target_ref = refs_by_source_id.get(edge.target)
        if not source_ref or not target_ref:
            continue
        relationship_objects.append(
            {
                "type": "relationship",
                "spec_version": "2.1",
                "id": _stix_id("relationship", investigation_id, edge.id),
                "created_by_ref": creator_ref,
                "created": created_at,
                "modified": modified_at,
                "relationship_type": _relationship_type(edge.label),
                "source_ref": source_ref,
                "target_ref": target_ref,
                "confidence": edge.confidence,
                "x_sentinel_source_edge_id": edge.id,
                "x_sentinel_epistemic_status": edge.epistemic_status,
                "x_sentinel_anomalous": edge.anomalous,
                "x_sentinel_evidence_record_ids": edge.evidence_record_ids,
                "x_sentinel_evidence_sha256": edge.evidence_hashes,
                "x_sentinel_source_channels": edge.source_types,
                **({"x_sentinel_observed_at": edge.observed_at} if edge.observed_at else {}),
            }
        )

    graph_receipt = hashlib.sha256(payload.model_dump_json().encode("utf-8")).hexdigest()
    object_refs = [item["id"] for item in [*entity_objects, *relationship_objects]]
    report = {
        "type": "report",
        "spec_version": "2.1",
        "id": _stix_id("report", investigation_id, graph_receipt),
        "created_by_ref": creator_ref,
        "created": created_at,
        "modified": modified_at,
        "name": f"{investigation.get('name', investigation_id)} intelligence graph",
        "description": (
            "Analyst-requested graph exchange. Observed relationships and derived review signals remain "
            "distinguished; recipients must verify against source evidence before action."
        ),
        "published": modified_at,
        "report_types": ["threat-report"],
        "object_refs": object_refs,
        "x_sentinel_investigation_id": investigation_id,
        "x_sentinel_classification": investigation.get("classification", "case-controlled"),
        "x_sentinel_graph_sha256": graph_receipt,
        "x_sentinel_handling": "human-review-required",
    }
    return {
        "type": "bundle",
        "id": f"bundle--{uuid4()}",
        "objects": [creator, *entity_objects, *relationship_objects, report],
    }
