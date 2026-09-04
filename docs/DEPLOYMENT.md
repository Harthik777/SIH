# Deploy the complete Sentinel website

Sentinel ships as one Docker web service: the first stage builds the React application, and the final Python image serves both the compiled site and FastAPI under one origin.

## Public internal-round edition (Render)

The repository includes `render.yaml` for a free Singapore-region Docker web service. The public configuration sets `SENTINEL_PUBLIC_DEMO=true`, which keeps every analysis screen available while rejecting arbitrary uploads. All bundled evidence is synthetic.

1. Push the repository to GitHub.
2. Open Render → **New → Blueprint** and connect `Harthik777/SIH`.
3. Confirm the `sentinel-sih-26189-harthik` free web service and deploy.
4. Wait for `/api/health` to pass, then open the assigned `onrender.com` URL.
5. Test `/?section=fusion&stage=1` and `/api/system/readiness`.

Render's free web service is appropriate for an internal-round preview, but it sleeps after inactivity and uses an ephemeral filesystem. The bundled investigation is rebuilt after restart; new audit events and demo decisions are not durable on the free tier. Do not upload real evidence to a public competition deployment.

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

Run the same image with `SENTINEL_PUBLIC_DEMO=false` only on a trusted network. Set a unique `SENTINEL_SECRET_KEY`, password, exact allowed origin, and durable volume for `/app/backend/data/investigations` and `/app/backend/data/uploads`. The full Docker Compose stack adds PostgreSQL, Neo4j, Redis, and Celery adapters for the next deployment tier.

The current competition API has a demo identity surface, not agency-grade endpoint authorization. Before accepting real evidence, enforce authentication on every request, add role/attribute checks, malware scanning, encrypted durable storage, retention controls, rate limits, and security review.
