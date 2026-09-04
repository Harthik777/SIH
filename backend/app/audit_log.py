"""Local append-only, hash-chained investigation audit log."""

from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


AUDIT_PATH = Path(__file__).resolve().parent.parent / "data" / "investigations" / "audit_chain.jsonl"
GENESIS_HASH = "0" * 64
_LOCK = threading.RLock()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _read_entries() -> list[dict[str, Any]]:
    if not AUDIT_PATH.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line in AUDIT_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries


def append_audit_event(
    action: str,
    target: str,
    details: dict[str, Any] | None = None,
    actor: str = "local-analyst",
) -> dict[str, Any]:
    """Append one event whose digest covers the preceding event's digest."""
    with _LOCK:
        entries = _read_entries()
        previous_hash = entries[-1]["hash"] if entries else GENESIS_HASH
        unsigned = {
            "sequence": len(entries) + 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": actor,
            "action": action,
            "target": target,
            "details": details or {},
            "previous_hash": previous_hash,
        }
        entry = {**unsigned, "hash": hashlib.sha256(_canonical(unsigned)).hexdigest()}
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_PATH.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return entry


def audit_entries(limit: int = 100) -> list[dict[str, Any]]:
    with _LOCK:
        return list(reversed(_read_entries()[-max(1, limit):]))


def verify_audit_chain() -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    previous_hash = GENESIS_HASH
    try:
        entries = _read_entries()
    except (OSError, json.JSONDecodeError) as exc:
        return {"valid": False, "entries": 0, "head": None, "errors": [{"sequence": None, "reason": str(exc)}], "method": "sha256-chain-v1"}
    for expected_sequence, entry in enumerate(entries, 1):
        recorded_hash = entry.get("hash")
        unsigned = {key: value for key, value in entry.items() if key != "hash"}
        calculated = hashlib.sha256(_canonical(unsigned)).hexdigest()
        if entry.get("sequence") != expected_sequence:
            errors.append({"sequence": expected_sequence, "reason": "sequence mismatch"})
        if entry.get("previous_hash") != previous_hash:
            errors.append({"sequence": expected_sequence, "reason": "previous hash mismatch"})
        if recorded_hash != calculated:
            errors.append({"sequence": expected_sequence, "reason": "content hash mismatch"})
        previous_hash = str(recorded_hash or "")
    return {
        "valid": not errors,
        "entries": len(entries),
        "head": entries[-1]["hash"] if entries else GENESIS_HASH,
        "errors": errors,
        "method": "sha256-chain-v1",
        "scope_note": "Local tamper-evidence, not a blockchain or a substitute for agency-grade immutable storage.",
    }
