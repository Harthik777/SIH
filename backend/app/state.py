from __future__ import annotations

import asyncio
import csv
import hashlib
import json
import re
import xml.etree.ElementTree as element_tree
from collections import defaultdict
from pathlib import Path
from typing import Any

from .config import get_settings
from .models import PipelineStage, PipelineState, UploadRecord


uploads: dict[str, UploadRecord] = {}
pipelines: dict[str, PipelineState] = {}
pipeline_events: dict[str, asyncio.Event] = defaultdict(asyncio.Event)

STAGES = [
    ("clean", "Validate & normalize"),
    ("entity", "Entity extraction"),
    ("relation", "Relation extraction"),
    ("graph", "Graph construction"),
    ("analysis", "Intelligence analysis"),
]


def make_pipeline(upload_id: str, activate: bool = True, requested_by: str = "local-analyst") -> PipelineState:
    return PipelineState(
        upload_id=upload_id,
        requested_by=requested_by,
        activate=activate,
        stages=[PipelineStage(id=stage_id, name=name) for stage_id, name in STAGES],
        logs=["Pipeline queued for local execution."],
    )


def _notify(pipeline_id: str) -> None:
    pipeline_events[pipeline_id].set()
    pipeline_events[pipeline_id] = asyncio.Event()


async def _progress(pipeline_id: str, stage: PipelineStage, values: tuple[int, ...] = (20, 55, 85, 100)) -> None:
    state = pipelines[pipeline_id]
    for value in values:
        stage.progress = value
        state.progress = round(sum(item.progress for item in state.stages) / len(state.stages))
        _notify(pipeline_id)
        await asyncio.sleep(0.08)


def _fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_text_source(path: Path) -> None:
    sample = path.read_bytes()[:1_048_576]
    if sample.startswith((b"MZ", b"\x7fELF", b"PK\x03\x04")):
        raise ValueError("Executable or archive content is not accepted as evidence text")
    if b"\x00" in sample:
        raise ValueError("Binary content is not accepted for this evidence format")


def _validate_rows(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    settings = get_settings()
    if len(rows) > settings.max_ingestion_records:
        raise ValueError(f"Source exceeds the {settings.max_ingestion_records:,}-record safety limit")
    normalized: list[dict[str, str]] = []
    for row_number, row in enumerate(rows, 1):
        if len(row) > settings.max_ingestion_columns:
            raise ValueError(f"Record {row_number} exceeds the {settings.max_ingestion_columns}-column safety limit")
        clean: dict[str, str] = {}
        for key, value in row.items():
            cell = "" if value is None else str(value)
            if len(cell) > settings.max_cell_characters:
                raise ValueError(f"Record {row_number} contains an oversized field")
            clean[str(key)] = cell
        normalized.append(clean)
    return normalized


def _profile(path: Path) -> tuple[dict[str, Any], list[dict[str, str]] | None]:
    _validate_text_source(path)
    suffix = path.suffix.lower()
    profile: dict[str, Any] = {
        "format": suffix.removeprefix(".").upper(),
        "bytes": path.stat().st_size,
        "sha256": _fingerprint(path),
    }
    structured_rows: list[dict[str, str]] | None = None

    if suffix == ".csv":
        settings = get_settings()
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if len(reader.fieldnames or []) > settings.max_ingestion_columns:
                raise ValueError(f"CSV exceeds the {settings.max_ingestion_columns}-column safety limit")
            raw_rows: list[dict[str, Any]] = []
            for row_number, row in enumerate(reader, 1):
                if row_number > settings.max_ingestion_records:
                    raise ValueError(f"CSV exceeds the {settings.max_ingestion_records:,}-record safety limit")
                raw_rows.append(row)
            structured_rows = _validate_rows(raw_rows)
        profile.update({"records": len(structured_rows), "columns": list(structured_rows[0]) if structured_rows else []})
    elif suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        records = payload if isinstance(payload, list) else payload.get("records", []) if isinstance(payload, dict) else []
        profile.update({"records": len(records), "root_type": type(payload).__name__})
        if records and all(isinstance(row, dict) for row in records):
            structured_rows = _validate_rows(records)
    elif suffix == ".txt":
        text = path.read_text(encoding="utf-8")
        blocks = [block.strip() for block in re.split(r"\n\s*---\s*\n|\n\s*\n", text) if block.strip()]
        case_blocks = [block for block in blocks if re.search(r"\bCase Number\b", block, re.IGNORECASE)]
        profile.update({"records": len(case_blocks) or len(blocks), "characters": len(text)})
        if case_blocks:
            from .crime_pipeline import parse_fir

            structured_rows = [
                {key: "" if value is None else str(value) for key, value in parse_fir(block).items()}
                for block in case_blocks
            ]
            profile["extraction"] = "deterministic FIR field parser"
    elif suffix in {".ttl", ".rdf"}:
        text = path.read_text(encoding="utf-8")
        profile.update({"records": len(re.findall(r"\brdf:type\b|\ba\s+(?:owl|crime):", text)), "semantic_format": True})
    elif suffix == ".xml":
        preamble = path.read_text(encoding="utf-8", errors="ignore")[:4096].casefold()
        if "<!doctype" in preamble or "<!entity" in preamble:
            raise ValueError("XML document type and entity declarations are not accepted")
        root = element_tree.parse(path).getroot()
        candidates = list(root) or [root]
        structured_rows = []
        for item in candidates:
            row: dict[str, str] = {}
            for element in item.iter():
                if list(element) or not (element.text or "").strip():
                    continue
                key = element.tag.rsplit("}", 1)[-1]
                row[key] = (element.text or "").strip()
            if row:
                structured_rows.append(row)
        structured_rows = _validate_rows(structured_rows)
        profile.update({"records": len(structured_rows), "root_element": root.tag, "extraction": "XML leaf-field mapper"})
    else:
        raise ValueError(f"Unsupported upload format: {suffix}")
    return profile, structured_rows


async def run_pipeline(pipeline_id: str, upload_dir: Path) -> None:
    state = pipelines[pipeline_id]
    upload = uploads[state.upload_id]
    candidate = (upload_dir / f"{upload.id}_{upload.filename}").resolve()
    current_stage: PipelineStage | None = None
    try:
        if upload_dir.resolve() not in candidate.parents or not candidate.is_file():
            raise FileNotFoundError("Uploaded source could not be resolved safely")
        state.status = "running"

        current_stage = state.stages[0]
        current_stage.status = "running"
        state.logs.append(f"Validating {upload.filename} ({candidate.stat().st_size:,} bytes).")
        profile, rows = _profile(candidate)
        await _progress(pipeline_id, current_stage)
        current_stage.status = "complete"
        state.logs.append(f"Integrity verified: SHA-256 {profile['sha256'][:16]}…; {profile['records']:,} record(s).")

        current_stage = state.stages[1]
        current_stage.status = "running"
        entity_counts: dict[str, int] = {}
        graph_payload = None
        if rows:
            from .crime_pipeline import build_graph

            graph_payload = build_graph(rows)
            for node in graph_payload.nodes:
                entity_counts[node.type] = entity_counts.get(node.type, 0) + 1
        await _progress(pipeline_id, current_stage)
        current_stage.status = "complete"
        state.logs.append(f"Entity extraction completed: {sum(entity_counts.values()):,} typed graph entities." if entity_counts else "Entity extraction completed; source retained for ontology mapping.")

        current_stage = state.stages[2]
        current_stage.status = "running"
        relationship_count = len(graph_payload.edges) if graph_payload else 0
        await _progress(pipeline_id, current_stage)
        current_stage.status = "complete"
        state.logs.append(f"Resolved {relationship_count:,} ontology-aligned relationship(s).")

        current_stage = state.stages[3]
        current_stage.status = "running"
        graph_metrics = {
            "nodes": len(graph_payload.nodes) if graph_payload else 0,
            "edges": len(graph_payload.edges) if graph_payload else 0,
        }
        await _progress(pipeline_id, current_stage)
        current_stage.status = "complete"
        state.logs.append(f"Graph artifact built with {graph_metrics['nodes']:,} nodes and {graph_metrics['edges']:,} edges." if graph_payload else "Source validated; graph construction awaits a compatible case schema.")

        current_stage = state.stages[4]
        current_stage.status = "running"
        risk_signals = sum(node.risk >= 85 for node in graph_payload.nodes) if graph_payload else 0
        await _progress(pipeline_id, current_stage)
        current_stage.status = "complete"
        state.result = {
            "source": profile,
            "entities": entity_counts,
            "graph": graph_metrics,
            "risk_signals": risk_signals,
            "provenance": {"algorithm": "SHA-256", "digest": profile["sha256"]},
        }
        if graph_payload and rows is not None:
            from .investigation_store import save_investigation

            investigation = save_investigation(
                graph_payload,
                rows,
                source_name=upload.filename,
                source_type=profile["format"],
                source_sha256=profile["sha256"],
                upload_id=upload.id,
                activate=state.activate,
                owner=state.requested_by,
            )
            state.result["investigation"] = investigation
            from .audit_log import append_audit_event

            append_audit_event(
                "investigation.create",
                investigation["id"],
                {
                    "source_upload": upload.id,
                    "records": investigation["records"],
                    "activated": investigation["active"],
                },
                actor=state.requested_by,
            )
            persistence = "in PostgreSQL-backed durable storage" if get_settings().persistence_mode != "local" else "as an atomic local snapshot"
            state.logs.append(
                f"Investigation snapshot {investigation['id']} stored {persistence}"
                + (" and activated." if investigation["active"] else ".")
            )
        state.status = "complete"
        upload.status = "complete"
        upload.records = int(profile["records"])
        if get_settings().persistence_mode != "local":
            from .database import update_persisted_upload

            update_persisted_upload(upload)
        state.logs.append(f"Analysis complete: {risk_signals:,} high-priority review signal(s); provenance manifest recorded.")
    except Exception as exc:
        if current_stage:
            current_stage.status = "failed"
        state.status = "failed"
        state.error = f"{type(exc).__name__}: {exc}"
        upload.status = "failed"
        if get_settings().persistence_mode != "local":
            from .database import update_persisted_upload

            update_persisted_upload(upload)
        state.logs.append(f"Pipeline stopped safely: {state.error}")
    finally:
        _notify(pipeline_id)


def remove_upload_file(upload_dir: Path, upload: UploadRecord) -> None:
    candidate = (upload_dir / f"{upload.id}_{upload.filename}").resolve()
    if upload_dir.resolve() in candidate.parents and candidate.exists():
        candidate.unlink()
