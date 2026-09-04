"""Durable, local-first investigation graph workspace.

The default supplied corpus is rebuilt from CSV for reproducibility. Compatible
uploads are stored as immutable JSON snapshots and can become the active graph.
No database or network service is required for this single-machine mode.
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .config import get_settings
from .crime_pipeline import DATASET_PATH, load_crime_graph, read_records
from .models import GraphPayload
from .suraksha import SURAKSHA_ID, SURAKSHA_PATH, load_suraksha_graph, load_suraksha_records, source_sha256


STORE_DIR = get_settings().investigation_dir
REGISTRY_PATH = STORE_DIR / "registry.json"
CITY_SHIELD_ID = "city-shield"
DEFAULT_INVESTIGATION_ID = SURAKSHA_ID
BUILT_IN_INVESTIGATION_IDS = {CITY_SHIELD_ID, SURAKSHA_ID}
_LOCK = threading.RLock()


def _city_shield_entry() -> dict[str, Any]:
    return {
        "id": CITY_SHIELD_ID,
        "name": "Operation City Shield",
        "source": DATASET_PATH.name,
        "source_type": "CSV",
        "records": len(read_records()),
        "created_at": datetime.fromtimestamp(DATASET_PATH.stat().st_mtime, timezone.utc).isoformat(),
        "status": "ready",
        "built_in": True,
        "classification": "supplied-demonstration-corpus",
    }


def _suraksha_entry() -> dict[str, Any]:
    payload = load_suraksha_graph()
    return {
        "id": SURAKSHA_ID,
        "name": "Operation Suraksha",
        "source": SURAKSHA_PATH.name,
        "source_type": "MULTI-SOURCE JSON",
        "source_sha256": source_sha256(),
        "records": len(load_suraksha_records()),
        "nodes": len(payload.nodes),
        "edges": len(payload.edges),
        "created_at": datetime.fromtimestamp(SURAKSHA_PATH.stat().st_mtime, timezone.utc).isoformat(),
        "status": "ready",
        "built_in": True,
        "featured": True,
        "classification": "synthetic-evaluation-only",
    }


def _built_in_entries() -> list[dict[str, Any]]:
    return [_suraksha_entry(), _city_shield_entry()]


def _registry() -> dict[str, Any]:
    if REGISTRY_PATH.exists():
        try:
            value = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
            if isinstance(value, dict) and isinstance(value.get("investigations"), list):
                return value
        except (OSError, json.JSONDecodeError):
            pass
    return {"active_id": DEFAULT_INVESTIGATION_ID, "investigations": []}


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        for attempt in range(6):
            try:
                temporary.replace(path)
                return
            except PermissionError:
                if attempt == 5:
                    raise
                time.sleep(0.05 * (attempt + 1))
    finally:
        if temporary.exists():
            try:
                temporary.unlink()
            except OSError:
                pass


def list_investigations() -> dict[str, Any]:
    with _LOCK:
        registry = _registry()
        items = [*_built_in_entries(), *(item for item in registry["investigations"] if item.get("id") not in BUILT_IN_INVESTIGATION_IDS)]
        active_id = registry.get("active_id", DEFAULT_INVESTIGATION_ID)
        if active_id not in BUILT_IN_INVESTIGATION_IDS and not (STORE_DIR / f"{active_id}.json").exists():
            active_id = DEFAULT_INVESTIGATION_ID
        mode = get_settings().persistence_mode
        persistence = {
            "local": "local-json-atomic",
            "postgres": "postgresql-durable-object-store+local-cache",
            "hybrid": "postgresql+neo4j+local-snapshot",
        }[mode]
        return {"active_id": active_id, "items": items, "persistence": persistence}


def active_investigation() -> dict[str, Any]:
    workspace = list_investigations()
    return next((item for item in workspace["items"] if item["id"] == workspace["active_id"]), _suraksha_entry())


def get_active_graph() -> GraphPayload:
    entry = active_investigation()
    if entry["id"] == SURAKSHA_ID:
        return load_suraksha_graph()
    if entry["id"] == CITY_SHIELD_ID:
        return load_crime_graph()
    snapshot_path = STORE_DIR / f"{entry['id']}.json"
    try:
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        return GraphPayload.model_validate(snapshot["graph"])
    except (OSError, KeyError, json.JSONDecodeError, ValueError):
        return load_crime_graph()


def get_active_records() -> list[dict[str, str]]:
    entry = active_investigation()
    if entry["id"] == SURAKSHA_ID:
        return load_suraksha_records()
    if entry["id"] == CITY_SHIELD_ID:
        return read_records()
    try:
        snapshot = json.loads((STORE_DIR / f"{entry['id']}.json").read_text(encoding="utf-8"))
        rows = snapshot.get("records", [])
        return [{str(key): "" if value is None else str(value) for key, value in row.items()} for row in rows if isinstance(row, dict)]
    except (OSError, json.JSONDecodeError):
        return []


def save_investigation(
    graph: GraphPayload,
    records: list[dict[str, str]],
    *,
    source_name: str,
    source_type: str,
    source_sha256: str,
    upload_id: str,
    activate: bool,
    owner: str = "local-analyst",
) -> dict[str, Any]:
    with _LOCK:
        investigation_id = f"inv-{uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        entry = {
            "id": investigation_id,
            "name": f"Investigation · {Path(source_name).stem[:48]}",
            "source": source_name,
            "source_type": source_type,
            "source_sha256": source_sha256,
            "upload_id": upload_id,
            "records": len(records),
            "nodes": len(graph.nodes),
            "edges": len(graph.edges),
            "created_at": now,
            "status": "ready",
            "built_in": False,
            "owner": owner,
            "access_scope": "case-owner",
        }
        snapshot_path = STORE_DIR / f"{investigation_id}.json"
        _write_json(
            snapshot_path,
            {"schema_version": 1, "investigation": entry, "graph": graph.model_dump(mode="json"), "records": records},
        )
        registry = _registry()
        registry["investigations"] = [
            item for item in registry["investigations"] if item.get("id") not in {*BUILT_IN_INVESTIGATION_IDS, investigation_id}
        ] + [entry]
        if activate:
            registry["active_id"] = investigation_id
        _write_json(REGISTRY_PATH, registry)
        if get_settings().persistence_mode != "local":
            from .database import persist_investigation, persist_state_path

            persist_state_path(snapshot_path)
            persist_state_path(REGISTRY_PATH)
            persist_investigation({**entry, "active": activate}, graph)
        return {**entry, "active": activate}


def activate_investigation(investigation_id: str) -> dict[str, Any]:
    with _LOCK:
        workspace = list_investigations()
        entry = next((item for item in workspace["items"] if item["id"] == investigation_id), None)
        if entry is None:
            raise KeyError(investigation_id)
        registry = _registry()
        registry["active_id"] = investigation_id
        _write_json(REGISTRY_PATH, registry)
        if get_settings().persistence_mode != "local":
            from .database import persist_state_path, set_persisted_active

            persist_state_path(REGISTRY_PATH)
            set_persisted_active(investigation_id)
        return {**entry, "active": True}


def delete_investigation(investigation_id: str) -> None:
    if investigation_id in BUILT_IN_INVESTIGATION_IDS:
        raise ValueError("The built-in investigation cannot be deleted")
    with _LOCK:
        registry = _registry()
        if not any(item.get("id") == investigation_id for item in registry["investigations"]):
            raise KeyError(investigation_id)
        registry["investigations"] = [item for item in registry["investigations"] if item.get("id") != investigation_id]
        if registry.get("active_id") == investigation_id:
            registry["active_id"] = DEFAULT_INVESTIGATION_ID
        _write_json(REGISTRY_PATH, registry)
        snapshot = (STORE_DIR / f"{investigation_id}.json").resolve()
        if STORE_DIR.resolve() in snapshot.parents:
            snapshot.unlink(missing_ok=True)
        if get_settings().persistence_mode != "local":
            from .database import delete_persisted_investigation, delete_state_path, persist_state_path

            persist_state_path(REGISTRY_PATH)
            delete_state_path(snapshot)
            delete_persisted_investigation(investigation_id)
