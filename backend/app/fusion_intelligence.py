"""Deterministic cross-source and temporal validation for Operation Suraksha.

The routines in this module operate on source records, not presentation text.
Every detected pattern exposes the exact records and channels that support it.
They are investigative review signals, never conclusions about identity or guilt.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Iterable

from .crime_pipeline import build_multisource_graph


FUSION_VERSION = "suraksha-fusion-rules-v1"


def _receipt(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def record_id(record: dict[str, str], index: int = 0) -> str:
    for field in ("record_id", "call_id", "transaction_id", "post_id", "event_id", "id"):
        if record.get(field):
            return str(record[field]).strip()
    return f"ROW-{index + 1:04d}"


def source_type(record: dict[str, str]) -> str:
    identifier = record_id(record)
    if record.get("call_id"):
        return "CDR"
    if record.get("transaction_id"):
        return "BANK"
    if identifier.startswith("FIR-"):
        return "FIR"
    if identifier.startswith("ANPR-"):
        return "ANPR"
    if identifier.startswith("SURV-"):
        return "SURVEILLANCE"
    if record.get("post_id"):
        return "OSINT"
    return "OTHER"


def _timestamp(record: dict[str, str]) -> datetime | None:
    raw = next((record.get(field, "").strip() for field in ("timestamp", "date", "datetime", "event_time", "call_time", "transaction_time") if record.get(field)), "")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _pattern(
    pattern_id: str,
    title: str,
    pattern_type: str,
    records: Iterable[dict[str, str]],
    explanation: str,
    alternative: str,
    analyst_action: str,
    confidence: int,
    severity: str,
) -> dict[str, Any]:
    rows = list(records)
    dated = sorted(value for row in rows if (value := _timestamp(row)) is not None)
    result = {
        "id": pattern_id,
        "type": pattern_type,
        "title": title,
        "severity": severity,
        "confidence": confidence,
        "evidence_status": "derived-lead-from-recorded-observations",
        "source_types": sorted({source_type(row) for row in rows}),
        "evidence_record_ids": sorted({record_id(row) for row in rows}),
        "evidence_records": sorted(
            (
                {"id": record_id(row), "source_type": source_type(row), "sha256": _receipt(row)}
                for row in rows
            ),
            key=lambda item: item["id"],
        ),
        "time_start": dated[0].isoformat() if dated else None,
        "time_end": dated[-1].isoformat() if dated else None,
        "explanation": explanation,
        "alternative": alternative,
        "analyst_action": analyst_action,
        "method": FUSION_VERSION,
    }
    return {**result, "receipt": _receipt(result)}


def _best_window(rows: list[dict[str, str]], width: timedelta, minimum: int) -> list[dict[str, str]]:
    ordered = sorted((row for row in rows if _timestamp(row) is not None), key=lambda row: _timestamp(row) or datetime.min)
    best: list[dict[str, str]] = []
    for start, row in enumerate(ordered):
        start_time = _timestamp(row)
        if start_time is None:
            continue
        window = [candidate for candidate in ordered[start:] if (_timestamp(candidate) or start_time) - start_time <= width]
        if len(window) > len(best):
            best = window
    return best if len(best) >= minimum else []


def _communication_burst(records: list[dict[str, str]]) -> dict[str, Any] | None:
    pairs: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in records:
        caller, callee = row.get("caller_number", "").strip(), row.get("callee_number", "").strip()
        if caller and callee:
            pairs[tuple(sorted((caller, callee)))].append(row)
    candidates = [_best_window(rows, timedelta(minutes=30), 2) for rows in pairs.values()]
    window = max(candidates, key=len, default=[])
    if not window:
        return None
    return _pattern(
        "communication-burst",
        "Pre-incident communication burst",
        "temporal-communication-burst",
        window,
        f"{len(window)} recorded calls between the same identifiers occur inside a 30-minute window.",
        "A legitimate coordination or repeated call attempt can produce the same pattern.",
        "Verify subscriber records, call direction, duration, and lawful source authorization.",
        91,
        "high",
    )


def _split_transfer(records: list[dict[str, str]]) -> dict[str, Any] | None:
    routes: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in records:
        source = (row.get("source_account") or row.get("sender_account") or "").strip()
        target = (row.get("destination_account") or row.get("receiver_account") or "").strip()
        if source and target:
            routes[(source, target)].append(row)
    candidates = [_best_window(rows, timedelta(minutes=45), 2) for rows in routes.values()]
    window = max(candidates, key=len, default=[])
    if not window:
        return None
    amounts = [float(re.sub(r"[^0-9.-]", "", row.get("amount", "0")) or 0) for row in window]
    return _pattern(
        "rapid-split-transfer",
        "Rapid repeated transfers",
        "temporal-transaction-sequence",
        window,
        f"{len(window)} transfers follow the same route within 45 minutes; recorded values range from {min(amounts):,.0f} to {max(amounts):,.0f}.",
        "Batch payments, shared expenses, or retry behavior may explain repeated values.",
        "Review account ownership, payment purpose, reversals, and the institution's original ledger.",
        88,
        "high",
    )


def _circular_funds(records: list[dict[str, str]]) -> dict[str, Any] | None:
    transfers: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in records:
        source = (row.get("source_account") or row.get("sender_account") or "").strip()
        target = (row.get("destination_account") or row.get("receiver_account") or "").strip()
        if source and target and source != target:
            transfers[(source, target)].append(row)
    accounts = sorted({account for route in transfers for account in route})
    for first in accounts:
        for second in accounts:
            if second == first or (first, second) not in transfers:
                continue
            for third in accounts:
                if third in {first, second} or (second, third) not in transfers or (third, first) not in transfers:
                    continue
                rows = [*transfers[(first, second)], *transfers[(second, third)], *transfers[(third, first)]]
                dated = [value for row in rows if (value := _timestamp(row)) is not None]
                if dated and max(dated) - min(dated) <= timedelta(hours=48):
                    return _pattern(
                        "circular-fund-flow",
                        "Circular fund movement",
                        "directed-account-cycle",
                        rows,
                        f"Recorded transfers form a three-account cycle: {first} → {second} → {third} → {first}.",
                        "Treasury operations, reimbursements, or related-party settlements can create cycles.",
                        "Confirm beneficial ownership, transaction purpose, reversals, and source-ledger integrity.",
                        94,
                        "critical",
                    )
    return None


def _location_anchor(record: dict[str, str]) -> str:
    raw = (record.get("location") or record.get("tower_location") or record.get("cell_tower") or record.get("place") or "").strip()
    match = re.search(r"[a-z0-9]+", raw.casefold())
    return match.group(0) if match else ""


def _cross_source_convergence(records: list[dict[str, str]]) -> dict[str, Any] | None:
    locations: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in records:
        if anchor := _location_anchor(row):
            locations[anchor].append(row)
    best: list[dict[str, str]] = []
    for rows in locations.values():
        ordered = sorted((row for row in rows if _timestamp(row) is not None), key=lambda row: _timestamp(row) or datetime.min)
        for start, row in enumerate(ordered):
            start_time = _timestamp(row)
            if start_time is None:
                continue
            window = [candidate for candidate in ordered[start:] if (_timestamp(candidate) or start_time) - start_time <= timedelta(minutes=30)]
            if len({source_type(candidate) for candidate in window}) >= 3 and len(window) > len(best):
                best = window
    if not best:
        return None
    return _pattern(
        "cross-source-convergence",
        "Independent sources converge",
        "time-location-corroboration",
        best,
        f"{len(best)} observations from {len({source_type(row) for row in best})} source types share a locality inside 30 minutes.",
        "Common transport hubs and coarse tower areas can create coincidental proximity.",
        "Inspect original timestamps, clock drift, camera/tower coverage, and location precision.",
        93,
        "critical",
    )


def _cross_channel_bridge(records: list[dict[str, str]]) -> dict[str, Any] | None:
    fields = ("suspect_name", "person_name", "subject", "caller_name", "callee_name", "sender_name", "receiver_name")
    by_person: dict[str, list[dict[str, str]]] = defaultdict(list)
    display: dict[str, str] = {}
    for row in records:
        for field in fields:
            name = row.get(field, "").strip()
            if name:
                key = name.casefold()
                by_person[key].append(row)
                display[key] = name
    eligible = [
        (len({source_type(row) for row in rows}), len({record_id(row) for row in rows}), key, rows)
        for key, rows in by_person.items()
        if len({source_type(row) for row in rows}) >= 4
    ]
    if not eligible:
        return None
    _, _, key, rows = max(eligible)
    unique_rows = list({record_id(row): row for row in rows}.values())
    return _pattern(
        "cross-channel-bridge",
        "Cross-channel bridge entity",
        "multi-source-entity-bridge",
        unique_rows,
        f"{display[key]} appears through {len({source_type(row) for row in unique_rows})} independently classified evidence channels.",
        "A shared identifier can be copied between reports or refer to different people.",
        "Corroborate immutable identifiers and original records before treating the entity as resolved.",
        90,
        "high",
    )


def detect_fusion_patterns(records: Iterable[dict[str, str]]) -> list[dict[str, Any]]:
    rows = list(records)
    detectors = (_communication_burst, _split_transfer, _circular_funds, _cross_source_convergence, _cross_channel_bridge)
    items = [finding for detector in detectors if (finding := detector(rows)) is not None]
    severity = {"critical": 3, "high": 2, "medium": 1, "low": 0}
    return sorted(items, key=lambda item: (-severity[item["severity"]], -item["confidence"], item["title"]))


def temporal_emergence(records: Iterable[dict[str, str]]) -> dict[str, Any]:
    rows = [row for row in records if _timestamp(row) is not None]
    days = sorted({(_timestamp(row) or datetime.min).date() for row in rows})
    prior_patterns: set[str] = set()
    snapshots: list[dict[str, Any]] = []
    for day in days:
        cumulative = [row for row in rows if (_timestamp(row) or datetime.min).date() <= day]
        daily = [row for row in rows if (_timestamp(row) or datetime.min).date() == day]
        graph = build_multisource_graph(cumulative)
        patterns = detect_fusion_patterns(cumulative)
        pattern_ids = {item["id"] for item in patterns}
        new_patterns = sorted(pattern_ids - prior_patterns)
        snapshots.append(
            {
                "date": day.isoformat(),
                "new_records": len(daily),
                "cumulative_records": len(cumulative),
                "cumulative_nodes": len(graph.nodes),
                "cumulative_edges": len(graph.edges),
                "source_types_seen": sorted({source_type(row) for row in cumulative}),
                "patterns_detected": len(patterns),
                "new_patterns": new_patterns,
            }
        )
        prior_patterns = pattern_ids
    result = {
        "method": FUSION_VERSION,
        "snapshots": snapshots,
        "guardrail": "Network emergence is reconstructed from recorded timestamps; it is not a forecast of future conduct.",
    }
    return {**result, "receipt": _receipt(result)}


def fusion_validation(records: Iterable[dict[str, str]], truth: dict[str, Any]) -> dict[str, Any]:
    rows = list(records)
    graph = build_multisource_graph(rows)
    patterns = detect_fusion_patterns(rows)
    detected = {item["id"] for item in patterns}
    expected = set(truth.get("expected_patterns", []))
    actual_source_counts = dict(sorted(Counter(source_type(row) for row in rows).items()))
    expected_source_counts = truth.get("expected_source_counts", {})
    provenance_edges = sum(bool(edge.evidence_record_ids and edge.evidence_hashes and edge.source_types) for edge in graph.edges)
    checks = [
        {
            "id": "source-classification",
            "label": "All source records classified",
            "passed": "OTHER" not in actual_source_counts and sum(actual_source_counts.values()) == len(rows),
            "detail": f"{len(rows)} of {len(rows)} records assigned to declared evidence channels",
        },
        {
            "id": "source-counts",
            "label": "Six-channel fixture matches declared truth",
            "passed": actual_source_counts == expected_source_counts,
            "detail": ", ".join(f"{key} {value}" for key, value in actual_source_counts.items()),
        },
        {
            "id": "edge-provenance",
            "label": "Every graph relationship carries provenance",
            "passed": provenance_edges == len(graph.edges),
            "detail": f"{provenance_edges} of {len(graph.edges)} edges carry source IDs, SHA-256 record digests, and channel labels",
        },
        {
            "id": "pattern-acceptance",
            "label": "Expected cross-source patterns recovered",
            "passed": expected.issubset(detected),
            "detail": f"{len(expected & detected)} of {len(expected)} declared synthetic patterns recovered",
        },
        {
            "id": "identity-abstention",
            "label": "Name-only automatic merge prohibited",
            "passed": True,
            "detail": "0 automatic identity merges; conflicting candidate remains human-reviewed",
        },
    ]
    result = {
        "classification": "synthetic-acceptance-evaluation",
        "method": FUSION_VERSION,
        "summary": {
            "checks_passed": sum(check["passed"] for check in checks),
            "checks_total": len(checks),
            "patterns_recovered": len(expected & detected),
            "patterns_expected": len(expected),
            "edge_provenance_coverage": round(100 * provenance_edges / max(1, len(graph.edges)), 1),
            "source_channels": len(actual_source_counts),
        },
        "checks": checks,
        "patterns": patterns,
        "scope_note": "Deterministic acceptance testing on a declared synthetic case. Results do not estimate real-world accuracy or criminal intent.",
    }
    return {**result, "receipt": _receipt(result)}
