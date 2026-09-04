"""Synthetic protected-person vault with masked-by-default disclosure."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .audit_log import append_audit_event


PROTECTED_PATH = Path(__file__).resolve().parent.parent / "data" / "operation_suraksha_protected.json"


@lru_cache(maxsize=1)
def _profiles() -> list[dict[str, Any]]:
    value = json.loads(PROTECTED_PATH.read_text(encoding="utf-8"))
    return value["profiles"]


def _mask_name(name: str) -> str:
    return " ".join(part[0] + "•" * max(2, len(part) - 1) for part in name.split())


def _mask_phone(phone: str) -> str:
    digits = "".join(character for character in phone if character.isdigit())
    return f"+{digits[:2]}-•••••••{digits[-3:]}" if len(digits) >= 5 else "WITHHELD"


def _masked(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": profile["id"],
        "graph_name": profile["graph_name"],
        "name": _mask_name(profile["legal_name"]),
        "phone": _mask_phone(profile["phone"]),
        "address": "WITHHELD — Karnataka",
        "status": "masked",
        "risk_scoring": "prohibited",
        "guardrail": profile["guardrail"],
    }


def masked_profiles() -> list[dict[str, Any]]:
    return [_masked(profile) for profile in _profiles()]


def reveal_profile(profile_id: str, reason: str, authorization_reference: str, actor: str) -> dict[str, Any]:
    profile = next((item for item in _profiles() if item["id"] == profile_id), None)
    if profile is None:
        raise KeyError(profile_id)
    event = append_audit_event(
        "protected-person.reveal",
        profile_id,
        {
            "authorization_reference": authorization_reference.strip(),
            "reason_sha256": hashlib.sha256(reason.strip().encode("utf-8")).hexdigest(),
            "fields_revealed": ["legal_name", "phone", "address"],
            "synthetic_fixture": True,
        },
        actor=actor,
    )
    return {
        "id": profile["id"],
        "graph_name": profile["graph_name"],
        "name": profile["legal_name"],
        "phone": profile["phone"],
        "address": profile["address"],
        "status": "revealed-for-current-response",
        "synthetic": True,
        "audit_hash": event["hash"],
        "guardrail": "Disclosure is ephemeral in this demo; the graph and exports remain pseudonymized.",
    }
