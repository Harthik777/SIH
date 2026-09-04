# Security and operations runbook

## Deployment profiles

| Profile | Purpose | Authentication | Evidence intake | Persistence |
| --- | --- | --- | --- | --- |
| Public Render | Competition evaluation | Synthetic demo identity | Disabled | Ephemeral runtime; bundled fixtures rebuild |
| Local development | Trusted developer machine | Optional | Enabled | Atomic local files |
| Private Docker | Single-machine investigative pilot | Required JWT; analyst/supervisor roles | Enabled | Docker volume + PostgreSQL + case-scoped Neo4j |

Never place real evidence in the public profile.

## Bootstrap the private profile

1. Copy `.env.example` to `.env`.
2. Generate a signing secret of at least 32 random characters.
3. Replace both default passwords. For unattended deployments, set `SENTINEL_ANALYST_PASSWORD_HASH` and `SENTINEL_SUPERVISOR_PASSWORD_HASH` to PBKDF2 values and omit plaintext secrets from committed files.
4. Restrict `SENTINEL_ALLOWED_ORIGINS` to the actual private web origin.
5. Start with `docker compose up --build` and confirm `/api/health/ready` passes.

Generate a compatible password hash locally:

```powershell
python -c "from backend.app.security import hash_password; import getpass; print(hash_password(getpass.getpass()))"
```

## Role boundary

- Viewer: authenticated read access.
- Analyst: evidence intake, pipeline execution, case activation, alert acknowledgement, reviewed identity dispositions and exports.
- Supervisor: analyst privileges plus protected-person reveal, configuration changes and investigation deletion.
- Public demo: supervisor-shaped interaction only over bundled fictional records; arbitrary uploads remain blocked.

Protected-person reveal still requires a reason and authorization reference, and the reason is hashed before entering the audit event.

## Monitoring

- `/api/health/live`: process liveness only.
- `/api/health/ready`: bundled artifacts, audit integrity, writable state, and configured persistence health.
- `/api/system/metrics`: compact operational JSON.
- `/metrics`: Prometheus-compatible counters and latency gauge.
- Every HTTP response carries `X-Request-ID` and `X-Response-Time-Ms`.

## Backup

Run `powershell -ExecutionPolicy Bypass -File scripts/backup_state.ps1`. The archive contains investigation snapshots, uploads and a SHA-256 manifest. Store backups on approved encrypted media outside the application host and test restoration under the agency's retention policy.

PostgreSQL and Neo4j require their normal database-native backups in addition to the application-state archive. The script is intentionally not presented as a complete database backup.

## Incident response minimum

1. Isolate the host and preserve the state volume.
2. Export and verify the audit chain; record its head hash separately.
3. Rotate signing and account secrets.
4. Review request IDs and reverse-proxy logs around the incident window.
5. Restore only from a verified archive and database backup.
6. Document any evidence exposure under the applicable legal and departmental process.

## Accreditation boundary

These controls make Sentinel a credible single-machine pilot. They do not replace agency SSO, hardware-backed keys, encryption-at-rest governance, malware scanning, DLP, SIEM integration, vulnerability assessment, penetration testing, independent model validation or legal accreditation.
