# Deploy the complete Sentinel website

Sentinel ships as one Docker web service: the first stage builds the React application, and the final Python image serves both the compiled site and FastAPI under one origin.

## Authenticated public web edition (Render)

The repository includes `render.yaml` for a free Singapore-region Docker web service plus managed PostgreSQL. The public URL runs the complete application with required authentication and `SENTINEL_PERSISTENCE_MODE=postgres`: analysts can upload evidence, execute the pipeline, activate investigations, and use every analysis and export module. PostgreSQL durably mirrors source files, investigation snapshots, active-case state, the audit chain, review decisions, runtime controls and OpenTimestamps proof artifacts; each object is SHA-256 checked before restoration into the service's local execution cache.

1. Push the repository to GitHub.
2. Open Render → **New → Blueprint** and connect `Harthik777/SIH`.
3. Confirm both the `sentinel-sih-26189-harthik` web service and `sentinel-sih-postgres` database, then apply the Blueprint.
4. In the service's **Environment** page, reveal or rotate `SENTINEL_ANALYST_PASSWORD` and `SENTINEL_SUPERVISOR_PASSWORD`. Keep them outside the repository and share the analyst credential with judges through an approved private channel.
5. Add the analyst email and password to GitHub Actions repository secrets named `SENTINEL_SMOKE_EMAIL` and `SENTINEL_SMOKE_PASSWORD`. The live-smoke workflow runs after successful release checks, daily, and manually; credentials and bearer tokens are never written to its logs or artifacts.
6. Wait for `/api/health` to report `auth_mode: required`, `public_demo: false`, and `persistence_mode: postgres`, then sign in at the assigned `onrender.com` URL.
7. Upload a synthetic sample, run the pipeline, activate its investigation, and verify that the graph and reports switch to the new case.

Render's free web process sleeps after inactivity and its filesystem is ephemeral, but application state is now restored from managed PostgreSQL after restart or redeploy. The Blueprint caps individual uploads at 25 MB to protect the free CPU/RAM and 1 GB database envelopes. Render's free PostgreSQL instance expires 30 days after creation, so this profile is a time-bounded competition deployment rather than permanent evidence custody. Before expiry, create a replacement Render database or point `SENTINEL_DATABASE_URL` at a compatible no-cost PostgreSQL provider such as Neon. Download important reports and proof bundles regardless. Use only synthetic or legally shareable redacted data—never operational FIR/CDR or survivor information.

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

## Optional self-hosted agency-pilot profile

Run `docker compose up --build` only on a trusted network after copying `.env.example` to `.env` and replacing its credentials. This optional profile sets `SENTINEL_AUTH_MODE=required`; the React application displays a login screen and every non-health API request requires a signed session. Analyst actions and supervisor-only actions are enforced server-side.

The `sentinel_state` Docker volume persists uploads, investigation snapshots, audit entries, and identity-review decisions. New investigations are catalogued in PostgreSQL and mirrored into Neo4j using investigation-scoped keys. Create a verified state archive with:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/backup_state.ps1
```

Operational endpoints are `/api/health/live`, `/api/health/ready`, `/api/system/metrics`, and Prometheus-compatible `/metrics`. This pilot includes text-content guards and rate limits, but real agency evidence still requires approved malware scanning, encryption/key management, retention controls, identity federation, penetration testing, and formal accreditation.

The private `.env` enables hybrid connectivity and OpenTimestamps by default. Set `SENTINEL_AUDIT_ANCHOR_MODE=disabled` or `SENTINEL_CONNECTIVITY_MODE=offline` for an air-gapped deployment. Online failure never blocks the evidence pipeline. Checkpoint submission and refresh are supervisor-only; only a nonce-blinded commitment is sent to the configured calendars. For the strongest independent verification, retain the downloaded files and verify them using an agency-operated Bitcoin Core node.

The release workflow has a separate `hybrid-persistence` job that boots actual PostgreSQL and Neo4j service containers. It round-trips two investigations whose local entity IDs deliberately collide and verifies they remain isolated, including relationship-level evidence hashes. This continuously validates the private adapters even when the development laptop does not have Docker installed.
