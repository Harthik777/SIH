#!/usr/bin/env python3
"""Credential-safe smoke test for the deployed Sentinel competition service.

The script deliberately uses only Python's standard library so the GitHub
runner does not need to install the application. It never prints the bearer
token or password. A successful run leaves a small, non-secret JSON receipt;
the generated report is validated in memory and never retained by GitHub.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "https://sentinel-sih-26189-harthik.onrender.com"
TRANSIENT_STATUSES = {408, 425, 429, 500, 502, 503, 504}


class SmokeFailure(RuntimeError):
    """A release-critical live assertion failed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeFailure(message)


def _url(base_url: str, path: str) -> str:
    return urljoin(f"{base_url.rstrip('/')}/", path.lstrip("/"))


def _request(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    token: str | None = None,
    payload: dict[str, Any] | None = None,
    attempts: int = 3,
    timeout: float = 30,
) -> tuple[int, dict[str, str], bytes]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {
        "Accept": "application/json",
        "User-Agent": "sentinel-live-smoke/1.0",
        "X-Request-ID": f"live-smoke-{int(time.time())}",
    }
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            request = Request(_url(base_url, path), data=body, headers=headers, method=method)
            with urlopen(request, timeout=timeout) as response:  # noqa: S310 - URL is operator-controlled
                return response.status, {key.lower(): value for key, value in response.headers.items()}, response.read()
        except HTTPError as exc:
            response_body = exc.read(512).decode("utf-8", errors="replace")
            if exc.code not in TRANSIENT_STATUSES or attempt == attempts:
                raise SmokeFailure(f"{method} {path} returned HTTP {exc.code}: {response_body}") from exc
            last_error = exc
        except (URLError, TimeoutError, OSError) as exc:
            if attempt == attempts:
                raise SmokeFailure(f"{method} {path} failed: {exc}") from exc
            last_error = exc
        time.sleep(min(5 * attempt, 15))
    raise SmokeFailure(f"{method} {path} failed: {last_error}")


def _json_response(*args: Any, **kwargs: Any) -> tuple[dict[str, Any], dict[str, str]]:
    status, headers, body = _request(*args, **kwargs)
    _require(status == 200, f"Expected HTTP 200, received {status}")
    try:
        value = json.loads(body)
    except json.JSONDecodeError as exc:
        raise SmokeFailure("Endpoint did not return valid JSON") from exc
    _require(isinstance(value, dict), "Endpoint returned a non-object JSON payload")
    return value, headers


def wait_for_release(base_url: str, expected_commit: str, wait_seconds: int) -> dict[str, Any]:
    deadline = time.monotonic() + wait_seconds
    last_detail = "no response"
    while time.monotonic() < deadline:
        try:
            health, _ = _json_response(base_url, "/api/health", attempts=1)
            actual_commit = str(health.get("deployment_commit", ""))
            if health.get("status") != "ok":
                last_detail = f"health status={health.get('status')!r}"
            elif expected_commit and actual_commit != expected_commit:
                last_detail = f"deployed commit {actual_commit or 'unreported'}; waiting for {expected_commit}"
            else:
                readiness, _ = _json_response(base_url, "/api/health/ready", attempts=1)
                if readiness.get("ready") is True:
                    return health
                failed = [item.get("id") for item in readiness.get("checks", []) if item.get("required") and not item.get("passed")]
                last_detail = f"readiness failed: {failed or 'unknown check'}"
        except SmokeFailure as exc:
            last_detail = str(exc)
        print(f"WAIT  {last_detail}", flush=True)
        time.sleep(15)
    raise SmokeFailure(f"Deployment did not become ready within {wait_seconds}s ({last_detail})")


def run_smoke(base_url: str, email: str, password: str, expected_commit: str, wait_seconds: int, output_dir: Path) -> dict[str, Any]:
    print(f"START {base_url}", flush=True)
    health = wait_for_release(base_url, expected_commit, wait_seconds)
    print(f"PASS  ready deployment {health.get('deployment_commit', 'unreported')}", flush=True)

    login, _ = _json_response(
        base_url,
        "/api/auth/login",
        method="POST",
        payload={"email": email, "password": password},
    )
    token = login.get("access_token")
    user = login.get("user", {})
    _require(isinstance(token, str) and len(token) > 40, "Login did not return a usable bearer token")
    _require(user.get("email") == email, "Login returned the wrong user")
    _require(user.get("role") in {"analyst", "supervisor"}, "Smoke account lacks analyst permissions")
    print(f"PASS  authenticated {user.get('role')} account", flush=True)

    replay, _ = _json_response(base_url, "/api/demo/suraksha/replay", token=token)
    _require(replay.get("investigation_id") == "operation-suraksha", "Flagship replay returned the wrong investigation")
    _require(replay.get("records") == 32, "Flagship replay no longer contains 32 source records")
    _require(replay.get("nodes") == 64 and replay.get("edges") == 148, "Flagship graph acceptance counts changed")
    _require(len(replay.get("steps", [])) == 6, "Flagship replay no longer contains six stages")
    _require(len(replay.get("source_counts", {})) == 6, "Flagship replay does not cover all six source channels")
    _require(isinstance(replay.get("receipt"), str) and len(replay["receipt"]) == 64, "Flagship replay receipt is missing")
    print("PASS  Operation Suraksha replay (32 records, 64 nodes, 148 edges)", flush=True)

    audit_before, _ = _json_response(base_url, "/api/audit/verify", token=token)
    _require(audit_before.get("valid") is True, "Audit chain is invalid before report export")
    _require(audit_before.get("method") == "sha256-chain-v1", "Unexpected audit verification method")
    print(f"PASS  audit chain valid ({audit_before.get('entries', 0)} entries)", flush=True)

    status, report_headers, report = _request(base_url, "/api/export/report/pdf", token=token)
    _require(status == 200, f"Report export returned HTTP {status}")
    _require("application/pdf" in report_headers.get("content-type", "").lower(), "Report export has the wrong content type")
    _require("sentinel_investigation_report.pdf" in report_headers.get("content-disposition", ""), "Report filename is missing")
    _require(report.startswith(b"%PDF-"), "Report export is not a PDF document")
    _require(len(report) >= 3_000, "Report export is unexpectedly small")
    _require(report.rstrip().endswith(b"%%EOF"), "Report export is truncated")
    print(f"PASS  PDF report export ({len(report):,} bytes)", flush=True)

    audit_after, _ = _json_response(base_url, "/api/audit/verify", token=token)
    _require(audit_after.get("valid") is True, "Audit chain is invalid after report export")
    _require(int(audit_after.get("entries", 0)) >= int(audit_before.get("entries", 0)) + 1, "Report export did not append an audit event")
    _require(audit_after.get("head") != audit_before.get("head"), "Audit head did not advance after report export")
    print(f"PASS  report export audited ({audit_after.get('entries', 0)} entries)", flush=True)

    output_dir.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema_version": 1,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "deployment_commit": health.get("deployment_commit"),
        "authenticated_role": user.get("role"),
        "replay": {key: replay.get(key) for key in ("investigation_id", "records", "nodes", "edges", "source_counts", "receipt")},
        "audit": {
            "valid": audit_after.get("valid"),
            "method": audit_after.get("method"),
            "entries_before_export": audit_before.get("entries"),
            "entries_after_export": audit_after.get("entries"),
            "head_after_export": audit_after.get("head"),
        },
        "report": {
            "filename": "sentinel_investigation_report.pdf",
            "bytes": len(report),
            "sha256": hashlib.sha256(report).hexdigest(),
            "content_type": report_headers.get("content-type"),
            "retained": False,
        },
    }
    (output_dir / "live_smoke_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print("PASS  live deployment smoke test complete", flush=True)
    return receipt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("SENTINEL_SMOKE_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--email", default=os.getenv("SENTINEL_SMOKE_EMAIL"))
    parser.add_argument("--password", default=os.getenv("SENTINEL_SMOKE_PASSWORD"))
    parser.add_argument("--expected-commit", default=os.getenv("SENTINEL_SMOKE_EXPECTED_COMMIT", ""))
    parser.add_argument("--wait-seconds", type=int, default=420)
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/live-smoke"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.email or not args.password:
        print("FAIL  SENTINEL_SMOKE_EMAIL and SENTINEL_SMOKE_PASSWORD must be configured as GitHub Actions secrets", file=sys.stderr)
        return 2
    try:
        run_smoke(args.base_url, args.email, args.password, args.expected_commit, args.wait_seconds, args.output_dir)
    except SmokeFailure as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
