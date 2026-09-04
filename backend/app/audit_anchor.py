"""Optional privacy-preserving external witness for the local audit chain.

The authoritative record remains Sentinel's append-only SHA-256 chain.  This
module checkpoints only its head: OpenTimestamps adds a random nonce before a
calendar sees the digest, and no evidence, identity, or audit-event content is
sent over the network.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from .audit_log import verify_audit_chain
from .config import get_settings


_LOCK = threading.RLock()
_SAFE_ID = re.compile(r"^[a-zA-Z0-9._-]{1,120}$")
_SUBMITTED_STATES = {"calendar-pending", "bitcoin-attested", "bitcoin-confirmed"}


class AnchorError(RuntimeError):
    pass


class AnchorDisabledError(AnchorError):
    pass


class AnchorLimitError(AnchorError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _anchor_dir() -> Path:
    path = get_settings().audit_anchor_dir
    path.mkdir(parents=True, exist_ok=True)
    return path


def _record_path(anchor_id: str) -> Path:
    if not _SAFE_ID.fullmatch(anchor_id):
        raise KeyError(anchor_id)
    return _anchor_dir() / f"{anchor_id}.record.json"


def _checkpoint_path(anchor_id: str) -> Path:
    return _anchor_dir() / f"{anchor_id}.checkpoint.json"


def _proof_path(anchor_id: str) -> Path:
    return _anchor_dir() / f"{anchor_id}.checkpoint.json.ots"


def _atomic_write(path: Path, payload: bytes) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)
    if get_settings().persistence_mode != "local":
        from .database import persist_state_path

        persist_state_path(path)


def _save_record(record: dict[str, Any]) -> None:
    _atomic_write(_record_path(record["id"]), _canonical(record) + b"\n")


def _read_record(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def list_audit_anchors() -> list[dict[str, Any]]:
    with _LOCK:
        records: list[dict[str, Any]] = []
        for path in _anchor_dir().glob("*.record.json"):
            try:
                records.append(_read_record(path))
            except (OSError, TypeError, json.JSONDecodeError):
                continue
        return sorted(records, key=lambda item: item.get("created_at", ""), reverse=True)


def anchor_service_status() -> dict[str, Any]:
    settings = get_settings()
    anchors = list_audit_anchors()
    submitted = sum(item.get("status") in _SUBMITTED_STATES for item in anchors)
    attempts = sum(int(item.get("submission_attempts", 0)) for item in anchors)
    enabled = settings.connectivity_mode == "hybrid" and settings.audit_anchor_mode == "opentimestamps"
    return {
        "connectivity_mode": settings.connectivity_mode,
        "online_capable": settings.connectivity_mode == "hybrid",
        "provider": "OpenTimestamps / Bitcoin" if settings.audit_anchor_mode == "opentimestamps" else "disabled",
        "submission_enabled": enabled,
        "submitted_checkpoints": submitted,
        "submission_attempts": attempts,
        "public_submission_limit": settings.audit_anchor_public_limit if settings.public_demo else None,
        "latest": anchors[0] if anchors else None,
        "privacy_boundary": "Only a nonce-blinded commitment to the audit-chain checkpoint is submitted; evidence and personal data remain off-chain.",
        "confirmation_boundary": "Calendar acceptance is pending, not Bitcoin confirmation. Confirmation is reported only after the proof is upgraded and checked against a Bitcoin block header.",
    }


def _new_checkpoint(actor: str) -> dict[str, Any]:
    verification = verify_audit_chain()
    if not verification["valid"]:
        raise AnchorError("Refusing to checkpoint an invalid audit chain")
    created = datetime.now(timezone.utc)
    created_at = created.isoformat()
    anchor_id = f"ots-{created.strftime('%Y%m%dT%H%M%SZ')}-{verification['head'][:12]}"
    checkpoint = {
        "schema": "sentinel-audit-checkpoint-v1",
        "created_at": created_at,
        "audit_method": verification["method"],
        "audit_entries": verification["entries"],
        "audit_head": verification["head"],
    }
    checkpoint_bytes = _canonical(checkpoint) + b"\n"
    record = {
        "id": anchor_id,
        "created_at": created_at,
        "created_by": actor,
        "status": "prepared",
        "provider": "OpenTimestamps / Bitcoin",
        "audit_head": verification["head"],
        "audit_entries": verification["entries"],
        "checkpoint_sha256": hashlib.sha256(checkpoint_bytes).hexdigest(),
        "calendar_commitment": None,
        "calendars_accepted": [],
        "proof_available": False,
        "submission_attempts": 0,
        "bitcoin": None,
        "last_error": None,
        "scope_note": "Prepared locally. No blockchain or third-party timestamp claim is made until a proof is submitted and later confirmed.",
    }
    _atomic_write(_checkpoint_path(anchor_id), checkpoint_bytes)
    _save_record(record)
    return record


def _submit_proof(checkpoint_path: Path, proof_path: Path, calendar_urls: list[str], timeout: float) -> tuple[str, list[str]]:
    try:
        from opentimestamps.calendar import RemoteCalendar
        from opentimestamps.core.op import OpAppend, OpSHA256
        from opentimestamps.core.serialize import BytesSerializationContext
        from opentimestamps.core.timestamp import DetachedTimestampFile
    except ImportError as exc:
        raise AnchorError("OpenTimestamps support is not installed") from exc

    with checkpoint_path.open("rb") as handle:
        detached = DetachedTimestampFile.from_fd(OpSHA256(), handle)
    nonce_tip = detached.timestamp.ops.add(OpAppend(os.urandom(16))).ops.add(OpSHA256())

    def submit(url: str):
        calendar = RemoteCalendar(url, user_agent="Sentinel-SIH/1.1")
        return url, calendar.submit(nonce_tip.msg, timeout=timeout)

    accepted: list[str] = []
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=min(3, len(calendar_urls))) as executor:
        futures = {executor.submit(submit, url): url for url in calendar_urls}
        for future in as_completed(futures):
            url = futures[future]
            try:
                accepted_url, timestamp = future.result()
                nonce_tip.merge(timestamp)
                accepted.append(accepted_url)
            except Exception as exc:  # remote failures are expected and must not expose response bodies
                failures.append(f"{url}: {type(exc).__name__}")
    if not accepted:
        raise AnchorError("No OpenTimestamps calendar accepted the checkpoint (" + ", ".join(failures) + ")")

    context = BytesSerializationContext()
    detached.serialize(context)
    _atomic_write(proof_path, context.getbytes())
    return nonce_tip.msg.hex(), accepted


def prepare_audit_anchor(actor: str, *, submit: bool = False) -> dict[str, Any]:
    settings = get_settings()
    with _LOCK:
        verification = verify_audit_chain()
        if not verification["valid"]:
            raise AnchorError("Refusing to checkpoint an invalid audit chain")
        existing = next((item for item in list_audit_anchors() if item.get("audit_head") == verification["head"]), None)
        record = existing or _new_checkpoint(actor)
        if not submit or record.get("status") in _SUBMITTED_STATES:
            return record
        if settings.connectivity_mode != "hybrid" or settings.audit_anchor_mode != "opentimestamps":
            raise AnchorDisabledError("Online OpenTimestamps submission is disabled for this deployment")
        if settings.public_demo:
            attempts = sum(int(item.get("submission_attempts", 0)) for item in list_audit_anchors())
            if attempts >= settings.audit_anchor_public_limit:
                raise AnchorLimitError("The public showcase has reached its safe checkpoint submission limit")
        calendars = settings.anchor_calendars
        if not calendars:
            raise AnchorDisabledError("No OpenTimestamps calendars are configured")
        record["submission_attempts"] = int(record.get("submission_attempts", 0)) + 1
        record["updated_at"] = _utc_now()
        _save_record(record)
        try:
            commitment, accepted = _submit_proof(
                _checkpoint_path(record["id"]),
                _proof_path(record["id"]),
                calendars,
                settings.audit_anchor_timeout_seconds,
            )
        except AnchorError as exc:
            record["status"] = "submission-failed"
            record["last_error"] = str(exc)
            record["updated_at"] = _utc_now()
            _save_record(record)
            raise
        record.update({
            "status": "calendar-pending",
            "submitted_at": _utc_now(),
            "updated_at": _utc_now(),
            "calendar_commitment": commitment,
            "calendars_accepted": accepted,
            "proof_available": True,
            "last_error": None,
            "scope_note": "Calendars accepted the blinded commitment. This is pending and is not yet a Bitcoin-confirmed timestamp.",
        })
        _save_record(record)
        return record


def _load_detached(anchor_id: str):
    from opentimestamps.core.serialize import StreamDeserializationContext
    from opentimestamps.core.timestamp import DetachedTimestampFile

    proof_bytes = _proof_path(anchor_id).read_bytes()
    return DetachedTimestampFile.deserialize(StreamDeserializationContext(io.BytesIO(proof_bytes)))


def _walk(timestamp):
    yield timestamp
    for child in timestamp.ops.values():
        yield from _walk(child)


def _safe_calendar_uri(uri: str) -> bool:
    try:
        parsed = urlparse(uri)
        if parsed.scheme != "https" or parsed.query or parsed.fragment or parsed.username or parsed.password:
            return False
        host = (parsed.hostname or "").casefold()
        return parsed.port in {None, 443} and any(host.endswith(suffix) for suffix in (
            ".calendar.opentimestamps.org",
            ".calendar.eternitywall.com",
            ".calendar.catallaxy.com",
        ))
    except ValueError:
        return False


def _upgrade_proof(detached, timeout: float) -> bool:
    from opentimestamps.calendar import CommitmentNotFoundError, RemoteCalendar
    from opentimestamps.core.notary import PendingAttestation

    changed = False
    attempts = 0
    for stamp in list(_walk(detached.timestamp)):
        pending = [item for item in stamp.attestations if isinstance(item, PendingAttestation)]
        for attestation in pending:
            if attempts >= 4 or not _safe_calendar_uri(attestation.uri):
                continue
            attempts += 1
            try:
                upgraded = RemoteCalendar(attestation.uri, user_agent="Sentinel-SIH/1.1").get_timestamp(stamp.msg, timeout=timeout)
            except (CommitmentNotFoundError, OSError, ValueError):
                continue
            before = {(type(item).__name__, repr(item)) for _, item in detached.timestamp.all_attestations()}
            stamp.merge(upgraded)
            after = {(type(item).__name__, repr(item)) for _, item in detached.timestamp.all_attestations()}
            changed = changed or after != before
    return changed


def _verify_bitcoin_attestation(detached, timeout: float) -> dict[str, Any] | None:
    from bitcoin.core import CBlockHeader, b2lx
    from opentimestamps.core.notary import BitcoinBlockHeaderAttestation

    api = get_settings().bitcoin_header_api.rstrip("/")
    for message, attestation in detached.timestamp.all_attestations():
        if not isinstance(attestation, BitcoinBlockHeaderAttestation):
            continue
        with httpx.Client(timeout=timeout, follow_redirects=False) as client:
            hash_response = client.get(f"{api}/block-height/{attestation.height}")
            hash_response.raise_for_status()
            block_hash = hash_response.text.strip()
            if not re.fullmatch(r"[0-9a-fA-F]{64}", block_hash):
                raise AnchorError("Bitcoin header service returned an invalid block hash")
            header_response = client.get(f"{api}/block/{block_hash}/header")
            header_response.raise_for_status()
            header_hex = header_response.text.strip()
            if not re.fullmatch(r"[0-9a-fA-F]{160}", header_hex):
                raise AnchorError("Bitcoin header service returned an invalid block header")
        header = CBlockHeader.deserialize(bytes.fromhex(header_hex))
        if b2lx(header.GetHash()) != block_hash.casefold():
            raise AnchorError("Bitcoin header hash does not match the requested best-chain block")
        block_time = attestation.verify_against_blockheader(message, header)
        return {
            "height": attestation.height,
            "block_hash": block_hash.lower(),
            "attested_at": datetime.fromtimestamp(block_time, timezone.utc).isoformat(),
            "verification_method": "OpenTimestamps proof + configured Esplora Bitcoin block header",
            "full_node_note": "For maximum trust minimization, verify the downloadable .ots proof with an independently operated Bitcoin Core node.",
        }
    return None


def refresh_audit_anchor(anchor_id: str) -> dict[str, Any]:
    settings = get_settings()
    if settings.connectivity_mode != "hybrid" or settings.audit_anchor_mode != "opentimestamps":
        raise AnchorDisabledError("Online OpenTimestamps refresh is disabled for this deployment")
    with _LOCK:
        path = _record_path(anchor_id)
        if not path.exists():
            raise KeyError(anchor_id)
        record = _read_record(path)
        if not record.get("proof_available"):
            raise AnchorError("This checkpoint has not been submitted to OpenTimestamps")
        detached = _load_detached(anchor_id)
        checkpoint_bytes = _checkpoint_path(anchor_id).read_bytes()
        if hashlib.sha256(checkpoint_bytes).digest() != detached.file_digest:
            raise AnchorError("Checkpoint content does not match its OpenTimestamps proof")
        changed = _upgrade_proof(detached, settings.audit_anchor_timeout_seconds)
        if changed:
            from opentimestamps.core.serialize import BytesSerializationContext

            context = BytesSerializationContext()
            detached.serialize(context)
            _atomic_write(_proof_path(anchor_id), context.getbytes())
        try:
            bitcoin = _verify_bitcoin_attestation(detached, settings.audit_anchor_timeout_seconds)
        except Exception as exc:
            bitcoin = None
            record["last_error"] = f"Bitcoin header verification pending: {type(exc).__name__}"
        if bitcoin:
            record["status"] = "bitcoin-confirmed"
            record["bitcoin"] = bitcoin
            record["last_error"] = None
            record["scope_note"] = "The upgraded proof matches a Bitcoin block header from the configured verifier. Independent Bitcoin Core verification remains the strongest check."
        elif any(type(item).__name__ == "BitcoinBlockHeaderAttestation" for _, item in detached.timestamp.all_attestations()):
            record["status"] = "bitcoin-attested"
            record["scope_note"] = "The proof contains a Bitcoin attestation, but independent block-header verification has not completed."
        else:
            record["status"] = "calendar-pending"
            record["scope_note"] = "Calendar receipt remains pending; Bitcoin aggregation commonly takes hours."
        record["updated_at"] = _utc_now()
        _save_record(record)
        return record


def proof_bytes(anchor_id: str) -> bytes:
    path = _proof_path(anchor_id)
    if not path.exists():
        raise KeyError(anchor_id)
    return path.read_bytes()


def checkpoint_bytes(anchor_id: str) -> bytes:
    path = _checkpoint_path(anchor_id)
    if not path.exists():
        raise KeyError(anchor_id)
    return path.read_bytes()
