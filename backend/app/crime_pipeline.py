"""Ontology-aligned crime extraction and graph construction.

This module adapts the supplied prototype pipeline for request-safe use. It keeps
model loading optional and fixes vehicle creation so records without plates do
not leak a stale/undefined ``plate`` value into the graph.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from .models import GraphEdge, GraphNode, GraphPayload


DATASET_PATH = Path(__file__).resolve().parent.parent / "data" / "crime_dataset.csv"

CRIME_RISK = {
    "HOMICIDE": 95,
    "ROBBERY": 84,
    "MOTOR VEHICLE THEFT": 74,
    "NARCOTICS": 70,
    "BURGLARY": 66,
    "ASSAULT": 64,
    "BATTERY": 56,
    "CRIMINAL DAMAGE": 51,
    "THEFT": 46,
}


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def _stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8"), usedforsecurity=False).hexdigest()[:12]
    return f"{prefix}_{digest}"


def _record_digest(record: dict[str, str]) -> str:
    encoded = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _risk_for_record(record: dict[str, str]) -> int:
    primary_type = record.get("primary_type", "").upper()
    description = record.get("description", "").upper()
    risk = CRIME_RISK.get(primary_type, 45)
    if "HANDGUN" in description or "WEAPON" in description:
        risk += 7
    if not _truthy(record.get("arrest")):
        risk += 4
    if _truthy(record.get("domestic")):
        risk += 5
    return min(risk, 99)


def read_records(path: Path = DATASET_PATH, limit: int | None = None) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        records = list(csv.DictReader(handle))
    return records[:limit] if limit else records


def parse_fir(fir_text: str) -> dict[str, Any]:
    """Extract the ontology fields from one FIR narrative without requiring spaCy."""
    patterns = {
        "case_number": r"\b([A-Z]{2}\d{6})\b",
        "suspect_name": r"identified\s+as\s+([A-Z][a-z]+\s+[A-Z][a-z]+)",
        "vehicle_plate": r"(?:license plate|bearing license plate)\s+([A-Z]{2}-\d{4}-[A-Z]{2})",
        "primary_type": r"incident of\s+(MOTOR VEHICLE THEFT|CRIMINAL DAMAGE|ARMED ROBBERY|ROBBERY|THEFT|BATTERY|BURGLARY|ASSAULT|NARCOTICS|HOMICIDE)",
        "description": r"involving\s+(.+?)\s+was reported",
        "block": r"reported at\s+(.+?),\s+situated",
        "district": r"District\s+(\d{3})",
        "beat": r"Beat\s+(\d{4})",
        "ward": r"Ward\s+(\d{1,2})",
        "community_area": r"Community Area\s+(\d{1,2})",
        "location_description": r"occurred on/at an?\s+(.+?)\.\s+The suspect",
        "iucr": r"IUCR code\s*([0-9]{3,4}[A-Z]?)",
        "fbi_code": r"FBI Code\s*([0-9]{1,2}[A-Z]?)",
    }
    result: dict[str, Any] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, fir_text, re.IGNORECASE)
        result[key] = match.group(1).strip() if match else None
    date_match = re.search(r"(\d{2}/\d{2}/\d{4})\s+at\s+(?:approximately\s+)?(\d{2}:\d{2})", fir_text)
    if date_match:
        parsed = datetime.strptime(" ".join(date_match.groups()), "%m/%d/%Y %H:%M")
        result["date"] = parsed.strftime("%Y-%m-%d %H:%M:%S")
        result["year"] = parsed.year
    else:
        result["date"], result["year"] = None, None
    result["arrest"] = bool(re.search(r"ARREST MADE", fir_text, re.IGNORECASE))
    result["domestic"] = bool(re.search(r"Domestic dispute:\s*YES", fir_text, re.IGNORECASE))
    return result


def build_graph(records: Iterable[dict[str, str]]) -> GraphPayload:
    records = list(records)
    if records and not {"case_number", "primary_type"}.issubset(records[0]):
        return build_multisource_graph(records)
    suspect_cases: Counter[str] = Counter(row.get("suspect_name", "") for row in records if row.get("suspect_name"))
    location_cases: Counter[str] = Counter(row.get("block", "") for row in records if row.get("block"))
    beat_cases: Counter[str] = Counter(row.get("beat", "") for row in records if row.get("beat"))
    grouped_risks: dict[tuple[str, str], list[int]] = defaultdict(list)
    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []

    def add_node(kind: str, raw_id: str, name: str, entity_type: str, risk: int, community: int, **extra: Any) -> str:
        node_id = _stable_id(kind, raw_id)
        if node_id not in nodes:
            nodes[node_id] = GraphNode(
                id=node_id, name=name, type=entity_type, risk=max(0, min(risk, 99)),
                confidence=96, community=community, **extra,
            )
        return node_id

    for index, record in enumerate(records):
        case_number = record.get("case_number", "").strip()
        if not case_number:
            continue
        primary_type = record.get("primary_type", "Unknown").strip() or "Unknown"
        district = record.get("district", "0").strip() or "0"
        community = (int(district) % 8) + 1 if district.isdigit() else 1
        risk = _risk_for_record(record)
        case_id = add_node(
            "case", case_number, f"Case {case_number}", "event", risk, community,
            description=f"{primary_type.title()} — {record.get('description', 'No description')}",
            location=record.get("block") or None, lastSeen=record.get("date") or None,
            tags=(
                (["arrest-made"] if _truthy(record.get("arrest")) else ["open"])
                + (["domestic"] if _truthy(record.get("domestic")) else [])
            ),
        )

        def link(target_id: str, label: str, confidence: int = 97, anomalous: bool = False) -> None:
            edges.append(
                GraphEdge(
                    id=f"edge_{len(edges)+1}",
                    source=case_id,
                    target=target_id,
                    label=label,
                    confidence=confidence,
                    anomalous=anomalous,
                    evidence_record_ids=[case_number],
                    evidence_hashes=[_record_digest(record)],
                    source_types=["FIR"],
                    observed_at=record.get("date") or None,
                )
            )

        suspect = record.get("suspect_name", "").strip()
        if suspect:
            suspect_risk = min(99, risk + min(12, (suspect_cases[suspect] - 1) * 4))
            suspect_id = add_node(
                "suspect", suspect, suspect, "person", suspect_risk, community,
                description=f"Named in {suspect_cases[suspect]} FIR record(s).",
                lastSeen=record.get("date") or None,
                tags=["repeat-subject"] if suspect_cases[suspect] > 1 else [],
            )
            link(suspect_id, "HAS_SUSPECT", anomalous=suspect_cases[suspect] > 1 or risk >= 88)
            plate = record.get("vehicle_plate", "").strip()
            if plate:  # Deliberately scoped: fixes the supplied prototype's undefined plate bug.
                vehicle_id = add_node("vehicle", plate, plate, "vehicle", min(95, suspect_risk + 2), community, description=f"Vehicle associated with {suspect}.", tags=["registered-vehicle"])
                edges.append(
                    GraphEdge(
                        id=f"edge_{len(edges)+1}",
                        source=suspect_id,
                        target=vehicle_id,
                        label="DRIVES_VEHICLE",
                        confidence=94,
                        anomalous=suspect_cases[suspect] > 1,
                        evidence_record_ids=[case_number],
                        evidence_hashes=[_record_digest(record)],
                        source_types=["FIR"],
                        observed_at=record.get("date") or None,
                    )
                )

        crime_id = add_node("crime", primary_type, primary_type.title(), "crime", CRIME_RISK.get(primary_type.upper(), 45), community, description=f"Ontology crime type present in {sum(1 for item in records if item.get('primary_type') == primary_type)} incidents.")
        link(crime_id, "HAS_CRIME_TYPE", 99, risk >= 88)

        block = record.get("block", "").strip()
        if block:
            location_risk = min(96, risk + min(10, (location_cases[block] - 1) * 3))
            location_id = add_node("location", block, block, "location", location_risk, community, description=f"{record.get('location_description','Unknown premise').title()} in District {district}.", location=block, tags=["repeat-location"] if location_cases[block] > 1 else [])
            link(location_id, "OCCURRED_AT", 98, location_cases[block] > 1 and risk >= 75)

        beat = record.get("beat", "").strip()
        if beat:
            grouped_risks[("beat", beat)].append(risk)
            beat_risk = round(sum(grouped_risks[("beat", beat)]) / len(grouped_risks[("beat", beat)]))
            beat_id = _stable_id("beat", beat)
            nodes[beat_id] = GraphNode(id=beat_id, name=f"Police Beat {beat}", type="location", risk=beat_risk, confidence=99, community=community, description=f"Operational area containing {beat_cases[beat]} incidents in this dataset.", location=f"District {district}", tags=["police-beat"])
            link(beat_id, "OCCURRED_IN_BEAT", 99)

    return GraphPayload(nodes=list(nodes.values()), edges=edges)


GENERIC_FIELDS: tuple[tuple[str, tuple[str, ...], str, str], ...] = (
    ("protected_person", ("protected_person_id",), "HAS_PROTECTED_PERSON", "protected_person"),
    ("person", ("suspect_name", "person", "person_name", "subject", "caller_name", "sender_name", "account_holder"), "MENTIONS_PERSON", "person"),
    ("person", ("associate_name", "callee_name", "receiver_name", "beneficiary_name"), "MENTIONS_ASSOCIATE", "person"),
    ("organization", ("organization", "organisation", "company", "employer", "merchant"), "MENTIONS_ORGANIZATION", "organization"),
    ("phone", ("phone_number", "mobile_number", "msisdn", "caller_number", "source_phone"), "HAS_SOURCE_PHONE", "phone"),
    ("phone", ("callee_number", "destination_phone", "receiver_phone"), "HAS_DESTINATION_PHONE", "phone"),
    ("account", ("account_number", "source_account", "sender_account", "wallet_address"), "HAS_SOURCE_ACCOUNT", "account"),
    ("account", ("destination_account", "receiver_account", "beneficiary_account"), "HAS_DESTINATION_ACCOUNT", "account"),
    ("vehicle", ("vehicle_plate", "license_plate", "registration_number"), "INVOLVES_VEHICLE", "vehicle"),
    ("location", ("location", "block", "address", "tower_location", "cell_tower", "place"), "OCCURRED_AT", "location"),
)


def _first_value(record: dict[str, str], aliases: tuple[str, ...]) -> tuple[str, str] | None:
    lowered = {str(key).strip().lower(): "" if value is None else str(value).strip() for key, value in record.items()}
    for alias in aliases:
        if lowered.get(alias):
            return alias, lowered[alias]
    return None


def _generic_risk(record: dict[str, str]) -> int:
    joined = " ".join(str(value) for value in record.values()).casefold()
    risk = 45
    risk += min(30, 10 * sum(token in joined for token in ("suspicious", "fraud", "threat", "ransom", "extortion", "weapon")))
    amount_value = _first_value(record, ("amount", "transaction_amount", "value"))
    if amount_value:
        try:
            amount = float(re.sub(r"[^0-9.-]", "", amount_value[1]))
            risk += 20 if amount >= 1_000_000 else 10 if amount >= 100_000 else 0
        except ValueError:
            pass
    return min(95, risk)


def build_multisource_graph(records: Iterable[dict[str, str]]) -> GraphPayload:
    """Map common CDR, transaction, surveillance, and OSINT columns to a graph.

    Field mappings are explicit and auditable; unknown fields remain in the source
    snapshot and are never invented as entities.
    """
    records = list(records)
    frequencies: Counter[tuple[str, str]] = Counter()
    for record in records:
        for entity_type, aliases, _, _ in GENERIC_FIELDS:
            match = _first_value(record, aliases)
            if match:
                frequencies[(entity_type, match[1].casefold())] += 1

    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []
    id_aliases = ("case_number", "record_id", "transaction_id", "call_id", "event_id", "post_id", "id")
    date_aliases = ("date", "timestamp", "datetime", "event_time", "call_time", "transaction_time")
    type_aliases = ("primary_type", "event_type", "record_type", "transaction_type", "call_type", "category", "source_type")

    def source_type(record: dict[str, str], identifier: str) -> str:
        if _first_value(record, ("call_id",)):
            return "CDR"
        if _first_value(record, ("transaction_id",)):
            return "BANK"
        if identifier.startswith("FIR-"):
            return "FIR"
        if identifier.startswith("ANPR-"):
            return "ANPR"
        if identifier.startswith("SURV-"):
            return "SURVEILLANCE"
        if _first_value(record, ("post_id",)):
            return "OSINT"
        return "OTHER"

    for index, record in enumerate(records, 1):
        identifier = (_first_value(record, id_aliases) or ("row", str(index)))[1]
        event_kind = (_first_value(record, type_aliases) or ("type", "source record"))[1]
        occurred_at = (_first_value(record, date_aliases) or ("date", ""))[1] or None
        record_source = source_type(record, identifier)
        risk = _generic_risk(record)
        community = int(hashlib.sha1(identifier.encode("utf-8"), usedforsecurity=False).hexdigest()[:4], 16) % 8 + 1
        event_id = _stable_id("record", identifier)
        description_fields = [f"{key}: {value}" for key, value in record.items() if str(value).strip()][:4]
        nodes[event_id] = GraphNode(
            id=event_id,
            name=f"{event_kind.title()} {identifier}",
            type="event",
            risk=risk,
            confidence=90,
            community=community,
            description=" · ".join(description_fields) or "Structured source record",
            lastSeen=occurred_at,
            tags=["source-observation", "generic-schema", f"source:{record_source.casefold()}"],
        )
        created: dict[str, str] = {}
        for entity_type, aliases, relation, prefix in GENERIC_FIELDS:
            match = _first_value(record, aliases)
            if not match:
                continue
            field, value = match
            normalized = re.sub(r"\s+", " ", value).strip()
            node_id = _stable_id(prefix, normalized.casefold())
            repeat_count = frequencies[(entity_type, normalized.casefold())]
            if node_id not in nodes:
                is_protected = entity_type == "protected_person"
                protected_labels = {
                    "PP-S-001": "Protected Person S-01",
                    "PP-S-002": "Protected Person S-02",
                }
                nodes[node_id] = GraphNode(
                    id=node_id,
                    name=protected_labels.get(normalized, "Protected Person") if is_protected else normalized,
                    type=entity_type,
                    risk=0 if is_protected else min(95, risk + min(15, max(0, repeat_count - 1) * 3)),
                    confidence=90,
                    community=community,
                    description=(
                        "Identity masked by policy. Protected people are excluded from criminal-risk "
                        "scoring and influence ranking."
                        if is_protected
                        else f"Observed in {repeat_count} source record(s) via field '{field}'."
                    ),
                    lastSeen=occurred_at,
                    tags=(
                        ["privacy-protected", "risk-scoring-prohibited"]
                        if is_protected
                        else (["repeat-entity"] if repeat_count > 1 else ["source-observation"])
                    ),
                )
            edges.append(
                GraphEdge(
                    id=f"edge_{len(edges)+1}",
                    source=event_id,
                    target=node_id,
                    label=relation,
                    confidence=90,
                    anomalous=False if entity_type == "protected_person" else repeat_count > 2 or risk >= 80,
                    evidence_record_ids=[identifier],
                    evidence_hashes=[_record_digest(record)],
                    source_types=[record_source],
                    observed_at=occurred_at,
                )
            )
            created[field] = node_id

        source_phone = created.get("caller_number") or created.get("source_phone")
        destination_phone = created.get("callee_number") or created.get("destination_phone") or created.get("receiver_phone")
        source_account = created.get("source_account") or created.get("sender_account")
        destination_account = created.get("destination_account") or created.get("receiver_account") or created.get("beneficiary_account")
        for source, target, relation in ((source_phone, destination_phone, "CALLED"), (source_account, destination_account, "TRANSFERRED_TO")):
            if source and target and source != target:
                edges.append(
                    GraphEdge(
                        id=f"edge_{len(edges)+1}",
                        source=source,
                        target=target,
                        label=relation,
                        confidence=96,
                        anomalous=risk >= 80,
                        evidence_record_ids=[identifier],
                        evidence_hashes=[_record_digest(record)],
                        source_types=[record_source],
                        observed_at=occurred_at,
                    )
                )

    return GraphPayload(nodes=list(nodes.values()), edges=edges)


@lru_cache(maxsize=1)
def load_crime_graph() -> GraphPayload:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Crime dataset not found: {DATASET_PATH}")
    return build_graph(read_records())
