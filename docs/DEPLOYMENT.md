# Deploy the complete Sentinel website

Sentinel ships as one Docker web service: the first stage builds the React application, and the final Python image serves both the compiled site and FastAPI under one origin.

## Public competition edition (Render)

The repository includes `render.yaml` for a free Singapore-region Docker web service. The public configuration sets `SENTINEL_PUBLIC_DEMO=true`, which keeps every analysis screen available while rejecting arbitrary uploads and disabling credential login. It also enables the optional OpenTimestamps adapter for audit-head checkpoints. All bundled evidence is synthetic.

1. Push the repository to GitHub.
2. Open Render → **New → Blueprint** and connect `Harthik777/SIH`.
3. Confirm the `sentinel-sih-26189-harthik` free web service and deploy.
4. Wait for `/api/health` to pass, then open the assigned `onrender.com` URL.
5. Test `/?section=fusion&stage=1` and `/api/system/readiness`.

Render's free web service is appropriate for competition judging, but it sleeps after inactivity and uses an ephemeral filesystem. The bundled investigation is rebuilt after restart; new audit events, demo decisions, checkpoints and proofs are not durable on the free tier. Download the proof bundle immediately after submission. Public instances permit at most three timestamp submission attempts to prevent calendar abuse. Do not upload real evidence to a public competition deployment.

OpenTimestamps calendar acceptance is initially shown as **calendar pending**. Bitcoin aggregation commonly takes hours; use **Check confirmation** later to upgrade the proof. The UI reports **Bitcoin confirmed** only after the upgraded proof matches a Bitcoin block header from the configured Esplora service.

## Immediate no-account preview

For a short internal demonstration, Cloudflare Quick Tunnel can expose the same public-safe process without opening inbound firewall ports:

```powershell
$env:SENTINEL_PUBLIC_DEMO = "true"
$env:SENTINEL_FRONTEND_DIST = "$PWD\frontend\dist"
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8001

# In a second terminal after installing cloudflared:
cloudflared tunnel --url http://localhost:8001
```

The generated `trycloudflare.com` address is temporary, changes when the tunnel restarts, has no uptime guarantee, and depends on this machine staying awake. Use Render for the stable submission URL.

## Local production-image rehearsal

```powershell
docker build -t sentinel-sih:local .
docker run --rm -p 8000:8000 `
  -e SENTINEL_PUBLIC_DEMO=true `
  -e SENTINEL_SECRET_KEY=local-rehearsal-secret `
  sentinel-sih:local
```

Open `http://localhost:8000`. Both frontend and API should load. Verify:

```powershell
Invoke-RestMethod http://localhost:8000/api/health
Invoke-RestMethod http://localhost:8000/api/system/readiness
```

## Private full-ingestion edition

Run `docker compose up --build` only on a trusted network after copying `.env.example` to `.env` and replacing its credentials. The private profile sets `SENTINEL_AUTH_MODE=required`; the React application displays a login screen and every non-health API request requires a signed session. Analyst actions and supervisor-only actions are enforced server-side.

The `sentinel_state` Docker volume persists uploads, investigation snapshots, audit entries, and identity-review decisions. New investigations are catalogued in PostgreSQL and mirrored into Neo4j using investigation-scoped keys. Create a verified state archive with:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/backup_state.ps1
```

Operational endpoints are `/api/health/live`, `/api/health/ready`, `/api/system/metrics`, and Prometheus-compatible `/metrics`. This pilot includes text-content guards and rate limits, but real agency evidence still requires approved malware scanning, encryption/key management, retention controls, identity federation, penetration testing, and formal accreditation.

The private `.env` enables hybrid connectivity and OpenTimestamps by default. Set `SENTINEL_AUDIT_ANCHOR_MODE=disabled` or `SENTINEL_CONNECTIVITY_MODE=offline` for an air-gapped deployment. Online failure never blocks the evidence pipeline. Checkpoint submission and refresh are supervisor-only; only a nonce-blinded commitment is sent to the configured calendars. For the strongest independent verification, retain the downloaded files and verify them using an agency-operated Bitcoin Core node.

The release workflow has a separate `hybrid-persistence` job that boots actual PostgreSQL and Neo4j service containers. It round-trips two investigations whose local entity IDs deliberately collide and verifies they remain isolated, including relationship-level evidence hashes. This continuously validates the private adapters even when the development laptop does not have Docker installed.
