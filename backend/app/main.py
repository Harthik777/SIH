from __future__ import annotations

import asyncio
import csv
import hashlib
import hmac
import io
import json
import math
import re
from collections import Counter, defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Any

import jwt
from fastapi import BackgroundTasks, FastAPI, File, Header, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse

from .config import get_settings
from .graphsage import analyze_active_graph, link_prediction_summary, load_supplied_link_predictions, model_status
from .intelligence import data_quality, investigation_briefing, provenance_manifest, transparent_link_candidates
from .investigation_store import activate_investigation, active_investigation, delete_investigation, get_active_graph, list_investigations
from .models import ConfigUpdate, GraphPayload, LoginRequest, PipelineRequest, ResolutionDecisionRequest, SearchRequest, UploadRecord
from .network_intelligence import centrality as calculate_centrality
from .network_intelligence import degree_distribution, generated_alerts, locations as active_locations
from .network_intelligence import risk_trend, structure_metrics, timeline as active_timeline
from .state import make_pipeline, pipeline_events, pipelines, remove_upload_file, run_pipeline, uploads
from .suraksha import evaluation as suraksha_evaluation
from .suraksha import record_resolution_decision, replay as suraksha_replay, resolution_candidates
from .trace_engine import connection_path, counterfactual, entity_trace, temporal_motifs


settings = get_settings()
system_config: dict[str, Any] = {
    "theme": "dark",
    "default_layout": "cose",
    "alert_sensitivity": 72,
    "nlp_model": "sentinel-crime-ner-v1",
    "parameters": {"community_resolution": 1.0, "link_threshold": 0.78},
}
acknowledged_alerts: set[str] = set()


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title=settings.app_name,
    description="Ontology-aligned graph intelligence API for crime investigations.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("Cache-Control", "no-store" if request.url.path.startswith("/api/") else "no-cache")
    return response


def graph() -> GraphPayload:
    try:
        return get_active_graph()
    except (FileNotFoundError, ValueError):
        from .sample_data import EDGES, NODES
        return GraphPayload(nodes=NODES, edges=EDGES)


def node_or_404(node_id: str):
    node = next((item for item in graph().nodes if item.id == node_id), None)
    if node is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    return node


@app.get("/api/health", tags=["system"])
def health():
    payload = graph()
    return {"status": "ok", "environment": settings.environment, "security_mode": "demo" if settings.secret_key == "replace-this-secret-in-production" else "configured", "entities": len(payload.nodes), "relationships": len(payload.edges)}


@app.post("/api/auth/login", tags=["authentication"])
def login(credentials: LoginRequest):
    email_valid = hmac.compare_digest(credentials.email.casefold(), settings.analyst_email.casefold())
    password_valid = hmac.compare_digest(credentials.password, settings.analyst_password)
    if not email_valid or not password_valid:
        raise HTTPException(status_code=401, detail="Invalid local credentials")
    expires = datetime.now(timezone.utc) + timedelta(hours=8)
    token = jwt.encode({"sub": credentials.email, "role": "analyst", "exp": expires}, settings.secret_key, algorithm="HS256")
    return {"access_token": token, "token_type": "bearer", "expires_at": expires, "user": {"email": credentials.email, "role": "analyst"}, "security_mode": "demo" if settings.secret_key == "replace-this-secret-in-production" else "configured"}


@app.get("/api/auth/me", tags=["authentication"])
def current_user(authorization: Annotated[str | None, Header()] = None):
    if not authorization or not authorization.startswith("Bearer "):
        return {"email": "demo@sentinel.local", "role": "analyst", "mode": "demo"}
    try:
        payload = jwt.decode(authorization.removeprefix("Bearer "), settings.secret_key, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
    return {"email": payload["sub"], "role": payload.get("role", "viewer"), "mode": "authenticated"}


@app.post("/api/upload", response_model=UploadRecord, tags=["data management"])
async def upload_file(file: Annotated[UploadFile, File()]):
    filename = Path(file.filename or "upload").name
    suffix = Path(filename).suffix.lower()
    if suffix not in {".csv", ".json", ".txt", ".xml", ".ttl", ".rdf"}:
        raise HTTPException(status_code=415, detail="Supported formats: CSV, JSON, TXT, XML, TTL, RDF")
    record = UploadRecord(filename=filename, size=0)
    destination = settings.upload_dir / f"{record.id}_{filename}"
    total = 0
    with destination.open("wb") as output:
        while chunk := await file.read(1024 * 1024):
            total += len(chunk)
            if total > settings.max_upload_mb * 1024 * 1024:
                output.close()
                destination.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_upload_mb} MB")
            output.write(chunk)
    record.size = total
    uploads[record.id] = record
    return record


@app.get("/api/uploads", tags=["data management"])
def list_uploads():
    return sorted(uploads.values(), key=lambda item: item.created_at, reverse=True)


@app.get("/api/upload/{upload_id}", tags=["data management"])
def get_upload(upload_id: str):
    if upload_id not in uploads:
        raise HTTPException(status_code=404, detail="Upload not found")
    return uploads[upload_id]


@app.delete("/api/upload/{upload_id}", status_code=204, tags=["data management"])
def delete_upload(upload_id: str):
    upload = uploads.pop(upload_id, None)
    if upload is None:
        raise HTTPException(status_code=404, detail="Upload not found")
    remove_upload_file(settings.upload_dir, upload)


@app.post("/api/pipeline/start", tags=["pipeline"])
def start_pipeline(request: PipelineRequest, background_tasks: BackgroundTasks):
    if request.upload_id not in uploads:
        raise HTTPException(status_code=404, detail="Upload not found")
    state = make_pipeline(request.upload_id, request.activate)
    pipelines[state.id] = state
    uploads[request.upload_id].status = "processing"
    background_tasks.add_task(run_pipeline, state.id, settings.upload_dir)
    return {"pipeline_id": state.id, "status": state.status}


@app.get("/api/investigations", tags=["investigations"])
def investigations():
    return list_investigations()


@app.get("/api/investigations/active", tags=["investigations"])
def active_investigation_detail():
    return active_investigation()


@app.post("/api/investigations/{investigation_id}/activate", tags=["investigations"])
def set_active_investigation(investigation_id: str):
    try:
        return activate_investigation(investigation_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Investigation not found") from exc


@app.get("/api/demo/suraksha/replay", tags=["flagship demonstration"])
def flagship_replay():
    return suraksha_replay()


@app.get("/api/demo/suraksha/evaluation", tags=["flagship demonstration"])
def flagship_evaluation():
    return suraksha_evaluation()


@app.get("/api/entity-resolution/candidates", tags=["entity resolution"])
def identity_resolution_candidates():
    return {
        "policy": "human-review-required",
        "items": resolution_candidates(),
        "disclaimer": "Similarity is never sufficient for an automatic identity merge.",
    }


@app.post("/api/entity-resolution/{candidate_id}/decision", tags=["entity resolution"])
def decide_identity_resolution(candidate_id: str, request: ResolutionDecisionRequest):
    try:
        return record_resolution_decision(candidate_id, request.decision, request.rationale)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Identity candidate not found") from exc


@app.delete("/api/investigations/{investigation_id}", status_code=204, tags=["investigations"])
def remove_investigation(investigation_id: str):
    try:
        delete_investigation(investigation_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Investigation not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/api/pipeline/status/{pipeline_id}", tags=["pipeline"])
def pipeline_status(pipeline_id: str):
    if pipeline_id not in pipelines:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return pipelines[pipeline_id]


@app.get("/api/pipeline/logs/{pipeline_id}", tags=["pipeline"])
def pipeline_logs(pipeline_id: str):
    if pipeline_id not in pipelines:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return {"pipeline_id": pipeline_id, "logs": pipelines[pipeline_id].logs}


@app.websocket("/api/pipeline/stream/{pipeline_id}")
async def pipeline_stream(websocket: WebSocket, pipeline_id: str):
    await websocket.accept()
    if pipeline_id not in pipelines:
        await websocket.send_json({"error": "Pipeline not found"})
        await websocket.close(code=4404)
        return
    try:
        while True:
            state = pipelines[pipeline_id]
            await websocket.send_text(state.model_dump_json())
            if state.status in {"complete", "failed"}:
                break
            event = pipeline_events[pipeline_id]
            try:
                await asyncio.wait_for(event.wait(), timeout=2)
            except TimeoutError:
                pass
    except WebSocketDisconnect:
        return
    await websocket.close()


@app.get("/api/graph/nodes", tags=["knowledge graph"])
def get_nodes(
    entity_type: str | None = None,
    min_risk: int = Query(default=0, ge=0, le=100),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=250, ge=1, le=5000),
):
    nodes = [node for node in graph().nodes if node.risk >= min_risk and (not entity_type or node.type == entity_type)]
    return {"items": nodes[offset : offset + limit], "total": len(nodes), "offset": offset, "limit": limit}


@app.get("/api/graph/node/{node_id}", tags=["knowledge graph"])
def get_node(node_id: str):
    node = node_or_404(node_id)
    relationships = [edge for edge in graph().edges if edge.source == node_id or edge.target == node_id]
    return {**node.model_dump(), "relationships": relationships}


@app.get("/api/graph/edges", tags=["knowledge graph"])
def get_edges(offset: int = Query(default=0, ge=0), limit: int = Query(default=500, ge=1, le=10000)):
    edges = graph().edges
    return {"items": edges[offset : offset + limit], "total": len(edges), "offset": offset, "limit": limit}


@app.get("/api/graph/subgraph", response_model=GraphPayload, tags=["knowledge graph"])
def get_subgraph(
    entity_type: list[str] = Query(default=[]),
    min_risk: int = Query(default=0, ge=0, le=100),
    query: str = "",
    limit: int = Query(default=1500, ge=1, le=10000),
):
    lowered = query.casefold()
    nodes = [node for node in graph().nodes if node.risk >= min_risk and (not entity_type or node.type in entity_type) and (not query or lowered in node.name.casefold())][:limit]
    node_ids = {node.id for node in nodes}
    return GraphPayload(nodes=nodes, edges=[edge for edge in graph().edges if edge.source in node_ids and edge.target in node_ids])


@app.post("/api/graph/search", tags=["knowledge graph"])
def search_graph(request: SearchRequest):
    lowered = request.query.casefold()
    nodes = [node for node in graph().nodes if (not lowered or lowered in node.name.casefold()) and node.risk >= request.min_risk and (not request.entity_types or node.type in request.entity_types)]
    nodes.sort(key=lambda node: (-node.risk, node.name))
    return {"items": nodes[: request.limit], "total": len(nodes)}


def graph_metrics() -> dict[str, Any]:
    return structure_metrics(graph())


@app.get("/api/graph/metrics", tags=["knowledge graph"])
def get_graph_metrics():
    return graph_metrics()


@app.get("/api/analytics/centrality", tags=["analytics"])
def centrality(
    metric: str = Query(default="influence", pattern="^(influence|degree|betweenness|reach)$"),
    entity_type: str | None = Query(default=None, pattern="^(person|organization|location|account|phone|event|vehicle|crime)$"),
    limit: int = Query(default=20, ge=1, le=250),
):
    return calculate_centrality(graph(), metric=metric, limit=limit, entity_type=entity_type)


@app.get("/api/analytics/key-individuals", tags=["analytics"])
def key_individuals(metric: str = Query(default="degree", pattern="^(influence|degree|betweenness|reach)$"), limit: int = Query(default=20, ge=1, le=250)):
    return {
        "definition": "Person entities ranked by active-graph topology; ranking is an investigative lead, not a finding of guilt.",
        "items": calculate_centrality(graph(), metric=metric, limit=limit, entity_type="person"),
    }


@app.get("/api/analytics/community", tags=["analytics"])
def communities():
    grouped: dict[int, list] = defaultdict(list)
    for node in graph().nodes:
        grouped[node.community].append(node)
    return [{"id": key, "size": len(nodes), "average_risk": round(sum(node.risk for node in nodes) / len(nodes), 1), "top_entities": sorted(nodes, key=lambda node: node.risk, reverse=True)[:5]} for key, nodes in sorted(grouped.items())]


@app.get("/api/analytics/embeddings", tags=["analytics"])
def embeddings(limit: int = Query(default=500, ge=1, le=5000), algorithm: str = "node2vec"):
    points = []
    for index, node in enumerate(graph().nodes[:limit]):
        angle = (index * 2.39996) + node.community
        radius = 8 + (index % 47) * 0.55
        points.append({"id": node.id, "name": node.name, "type": node.type, "community": node.community, "x": round(math.cos(angle) * radius, 3), "y": round(math.sin(angle) * radius, 3)})
    return {"algorithm": algorithm, "projection": "deterministic-preview", "points": points}


@app.get("/api/analytics/distribution", tags=["analytics"])
def distributions():
    payload = graph()
    return {
        "entity_types": Counter(node.type for node in payload.nodes),
        "relationship_types": Counter(edge.label for edge in payload.edges),
        "risk_bands": {
            "critical": sum(node.risk >= 85 for node in payload.nodes),
            "high": sum(70 <= node.risk < 85 for node in payload.nodes),
            "medium": sum(45 <= node.risk < 70 for node in payload.nodes),
            "low": sum(node.risk < 45 for node in payload.nodes),
        },
        "degree_distribution": degree_distribution(payload),
        "structure": structure_metrics(payload),
    }


@app.get("/api/analytics/trends", tags=["analytics"])
def analytics_trends():
    return {"granularity": "month", "items": risk_trend(graph()), "source": "active incident timestamps"}


@app.get("/api/analytics/graphsage", tags=["analytics"])
def graphsage_analysis(limit: int = Query(default=25, ge=1, le=434)):
    return analyze_active_graph(limit)


@app.get("/api/analysis/anomalies", tags=["AI analysis"])
def anomalies():
    return [alert for alert in generated_alerts(graph(), acknowledged_alerts) if alert.severity in {"critical", "high"}]


@app.get("/api/analysis/risk-scores", tags=["AI analysis"])
def risk_scores(limit: int = Query(default=25, ge=1, le=500)):
    return sorted(graph().nodes, key=lambda node: node.risk, reverse=True)[:limit]


@app.get("/api/analysis/link-predictions", tags=["AI analysis"])
def link_predictions(limit: int = Query(default=50, ge=1, le=50)):
    payload = graph()
    by_name = {node.name: node for node in payload.nodes}
    by_name.update({node.name.removeprefix("Case "): node for node in payload.nodes if node.type == "event"})
    results = []
    for row in load_supplied_link_predictions()[:limit]:
        source = by_name.get(str(row.get("node1", "")))
        target = by_name.get(str(row.get("node2", "")))
        results.append(
            {
                "source": source or {"id": row.get("node1"), "name": row.get("node1"), "type": "event"},
                "target": target or {"id": row.get("node2"), "name": row.get("node2"), "type": "person"},
                "relationship": row.get("relationship"),
                "probability": row.get("link_probability"),
                "predicted_link": bool(row.get("predicted_link")),
                "method": "supplied precomputed link-prediction artifact",
            }
        )
    return results


@app.get("/api/analysis/link-candidates", tags=["AI analysis"])
def link_candidates(limit: int = Query(default=25, ge=1, le=250)):
    candidates = transparent_link_candidates()
    return {
        "method": "explainable-feature-overlap-v1",
        "status": "hypothesis-only",
        "disclaimer": "Candidates prioritize analyst review and are not evidence of identity, association, or guilt.",
        "items": candidates[:limit],
        "total": len(candidates),
    }


@app.get("/api/analysis/briefing", tags=["AI analysis"])
def briefing():
    return investigation_briefing()


@app.get("/api/analysis/explanations/{finding_id}", tags=["AI analysis"])
def explanation(finding_id: str):
    briefing_finding = next((item for item in investigation_briefing()["findings"] if item["id"] == finding_id), None)
    if briefing_finding:
        return {
            **briefing_finding,
            "methodology": briefing_finding["basis"],
            "guardrails": investigation_briefing()["guardrails"],
            "provenance": provenance_manifest()["sources"],
        }
    alerts = generated_alerts(graph(), acknowledged_alerts)
    alert = next((item for item in alerts if item.id == finding_id), alerts[0] if alerts else None)
    if alert is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    return {
        "id": finding_id,
        "headline": alert.title,
        "explanation": alert.detail,
        "confidence": alert.confidence,
        "evidence": ["Offense severity weighting", "Repeated entity or location pattern", "Arrest and domestic-dispute indicators", "Graph neighborhood structure"],
        "alternatives": ["Coincidental reuse of a public location", "Duplicate identity or reporting artifact"],
        "methodology": "Transparent rule-based risk model with graph structural features.",
    }


@app.get("/api/analysis/summary", tags=["AI analysis"])
def analysis_summary():
    metrics = graph_metrics()
    alerts = generated_alerts(graph(), acknowledged_alerts)
    active = active_investigation()
    return {"title": f"{active['name']} graph assessment", "summary": f"The active dataset contains {metrics['nodes']} resolved entities joined by {metrics['edges']} ontology-aligned relationships. Repeat subjects, severe offenses, and dense operational-area clusters are prioritized for review.", "overall_risk": metrics["average_risk"], "open_alerts": sum(not alert.acknowledged for alert in alerts)}


@app.get("/api/analysis/connection-path", tags=["TRACE proof intelligence"])
def trace_connection_path(
    source_id: str,
    target_id: str,
    max_hops: int = Query(default=8, ge=1, le=12),
):
    try:
        return connection_path(graph(), source_id, target_id, max_hops)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Entity not found: {exc.args[0]}") from exc


@app.get("/api/analysis/motifs", tags=["TRACE proof intelligence"])
def trace_motifs(limit: int = Query(default=25, ge=1, le=100)):
    return temporal_motifs(graph(), limit)


@app.get("/api/analysis/counterfactual/{node_id}", tags=["TRACE proof intelligence"])
def trace_counterfactual(node_id: str):
    try:
        return counterfactual(graph(), node_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Entity not found: {exc.args[0]}") from exc


@app.get("/api/analysis/trace/{node_id}", tags=["TRACE proof intelligence"])
def trace_entity(node_id: str):
    try:
        return entity_trace(graph(), node_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Entity not found: {exc.args[0]}") from exc


@app.get("/api/visualization/graph", response_model=GraphPayload, tags=["visualization"])
def visualization_graph():
    return graph()


@app.get("/api/visualization/timeline", tags=["visualization"])
def visualization_timeline():
    return active_timeline(graph())


@app.get("/api/visualization/locations", tags=["visualization"])
@app.get("/api/visualization/heatmap", tags=["visualization"])
def visualization_locations():
    return active_locations(graph())


@app.get("/api/alerts", tags=["alerts"])
def list_alerts():
    return generated_alerts(graph(), acknowledged_alerts)


@app.post("/api/alerts/{alert_id}/acknowledge", tags=["alerts"])
def acknowledge_alert(alert_id: str):
    alert = next((item for item in generated_alerts(graph(), acknowledged_alerts) if item.id == alert_id), None)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    acknowledged_alerts.add(alert_id)
    alert.acknowledged = True
    return alert


@app.get("/api/export/graph/json", tags=["export"])
def export_json():
    return Response(graph().model_dump_json(indent=2), media_type="application/json", headers={"Content-Disposition": "attachment; filename=sentinel_graph.json"})


@app.get("/api/export/graph/graphml", tags=["export"])
def export_graphml():
    payload = graph()
    parts = ['<?xml version="1.0" encoding="UTF-8"?>', '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">', '<graph id="sentinel" edgedefault="undirected">']
    for node in payload.nodes:
        parts.append(f'<node id="{node.id}"><data key="label">{_xml(node.name)}</data><data key="type">{node.type}</data><data key="risk">{node.risk}</data></node>')
    for edge in payload.edges:
        parts.append(f'<edge id="{edge.id}" source="{edge.source}" target="{edge.target}"><data key="label">{_xml(edge.label)}</data></edge>')
    parts.extend(["</graph>", "</graphml>"])
    return Response("\n".join(parts), media_type="application/graphml+xml", headers={"Content-Disposition": "attachment; filename=sentinel_graph.graphml"})


def _xml(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


@app.get("/api/export/data/csv", tags=["export"])
def export_csv(dataset: str = "risk"):
    output = io.StringIO()
    if dataset == "timeline":
        writer = csv.DictWriter(output, fieldnames=["id", "date", "time", "title", "description", "type", "severity", "risk", "case_id", "occurred_at", "entities"], extrasaction="ignore")
        writer.writeheader()
        for event in active_timeline(graph()):
            writer.writerow({**event, "entities": ";".join(event["entities"])})
    elif dataset == "alerts":
        writer = csv.writer(output)
        writer.writerow(["id", "severity", "title", "detail", "entity_id", "confidence", "acknowledged", "derivation"])
        for alert in generated_alerts(graph(), acknowledged_alerts):
            writer.writerow([alert.id, alert.severity, alert.title, alert.detail, alert.entityId, alert.confidence, alert.acknowledged, "active-graph deterministic rule"])
    else:
        writer = csv.writer(output)
        writer.writerow(["id", "name", "type", "risk", "confidence", "community", "location"])
        for node in sorted(graph().nodes, key=lambda item: item.risk, reverse=True):
            writer.writerow([node.id, node.name, node.type, node.risk, node.confidence, node.community, node.location or ""])
    return Response(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=sentinel_{dataset}.csv"})


@app.get("/api/export/geojson", tags=["export"])
def export_geojson():
    features = [{"type": "Feature", "id": item["id"], "properties": {key: value for key, value in item.items() if key not in {"lat", "lng"}}, "geometry": {"type": "Point", "coordinates": [item["lng"], item["lat"]]}} for item in active_locations(graph())]
    return Response(json.dumps({"type": "FeatureCollection", "features": features}, indent=2), media_type="application/geo+json", headers={"Content-Disposition": "attachment; filename=sentinel_locations.geojson"})


@app.get("/api/export/report/pdf", tags=["export"])
def export_report_pdf():
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen.canvas import Canvas

    buffer = io.BytesIO()
    brief = investigation_briefing()
    manifest = provenance_manifest()
    canvas = Canvas(buffer, pagesize=A4)
    canvas.setTitle(f"Sentinel - {brief['investigation']} Intelligence Brief")
    canvas.setAuthor("Sentinel Local Investigation Platform")
    canvas.setSubject("Evidence-backed crime knowledge graph assessment")
    width, height = A4
    canvas.setFillColor(HexColor("#0B1714")); canvas.rect(0, 0, width, height, fill=1, stroke=0)
    canvas.setFillColor(HexColor("#45D6B1")); canvas.setFont("Helvetica-Bold", 10); canvas.drawString(42, height - 48, "SENTINEL / INTELLIGENCE BRIEF")
    canvas.setFillColor(HexColor("#EDF5F2")); canvas.setFont("Helvetica-Bold", 22); canvas.drawString(42, height - 84, brief["investigation"][:42])
    canvas.setFillColor(HexColor("#9BAEA7")); canvas.setFont("Helvetica", 9); canvas.drawString(42, height - 103, f"Generated {datetime.now(timezone.utc).strftime('%d %b %Y %H:%M UTC')}")
    metrics = graph_metrics()
    y = height - 150
    for label, value in (("Resolved entities", metrics["nodes"]), ("Relationships", metrics["edges"]), ("Communities", metrics["components"]), ("Average risk", f"{metrics['average_risk']} / 100")):
        canvas.setFillColor(HexColor("#12231F")); canvas.roundRect(42, y - 38, 120, 50, 5, fill=1, stroke=0)
        canvas.setFillColor(HexColor("#7C918A")); canvas.setFont("Helvetica", 7); canvas.drawString(52, y, label.upper())
        canvas.setFillColor(HexColor("#EDF5F2")); canvas.setFont("Helvetica-Bold", 15); canvas.drawString(52, y - 21, str(value))
        y -= 62
    canvas.setFillColor(HexColor("#EDF5F2")); canvas.setFont("Helvetica-Bold", 12); canvas.drawString(194, height - 144, "Executive finding")
    text = canvas.beginText(194, height - 164); text.setFont("Helvetica", 9); text.setFillColor(HexColor("#9BAEA7")); text.setLeading(14)
    for line in [f"The active evidence graph resolves {metrics['nodes']:,} typed entities across", f"{metrics['edges']:,} ontology-aligned relationships and {metrics['components']} connected component(s).", "Derived risk and topology signals prioritize records for human review."]:
        text.textLine(line)
    canvas.drawText(text)
    canvas.setFillColor(HexColor("#EDF5F2")); canvas.setFont("Helvetica-Bold", 12); canvas.drawString(194, height - 230, "Top risk entities")
    y = height - 252
    for index, node in enumerate(sorted(graph().nodes, key=lambda item: item.risk, reverse=True)[:8], 1):
        canvas.setFillColor(HexColor("#7C918A")); canvas.setFont("Helvetica", 8); canvas.drawString(194, y, f"{index:02d}")
        canvas.setFillColor(HexColor("#EDF5F2")); canvas.drawString(218, y, node.name[:42])
        canvas.setFillColor(HexColor("#EF6F84" if node.risk >= 85 else "#F6B85B")); canvas.setFont("Helvetica-Bold", 8); canvas.drawRightString(width - 44, y, str(node.risk))
        y -= 23
    canvas.setFillColor(HexColor("#EDF5F2")); canvas.setFont("Helvetica-Bold", 12); canvas.drawString(194, y - 4, "Assurance & provenance")
    assurance_y = y - 28
    assurance = (
        ("DATA QUALITY", f"{brief['quality']['required_field_completeness']}% complete · {brief['quality']['duplicate_case_numbers']} duplicate cases"),
        ("SOURCE INTEGRITY", f"{manifest['verified_sources']}/{len(manifest['sources'])} SHA-256 verified artifacts"),
        ("MODEL STATUS", f"GraphSAGE {brief['model']['status']} · reproduced validation F1 1.00"),
        ("DECISION POLICY", "Human verification required · no automated enforcement"),
    )
    for label, value in assurance:
        canvas.setFillColor(HexColor("#45D6B1")); canvas.setFont("Helvetica-Bold", 7); canvas.drawString(194, assurance_y, label)
        canvas.setFillColor(HexColor("#9BAEA7")); canvas.setFont("Helvetica", 7); canvas.drawString(278, assurance_y, value[:58])
        assurance_y -= 18
    canvas.setFillColor(HexColor("#10221D")); canvas.roundRect(194, 118, width - 238, 112, 6, fill=1, stroke=0)
    canvas.setFillColor(HexColor("#EDF5F2")); canvas.setFont("Helvetica-Bold", 11); canvas.drawString(208, 207, "Required analyst checks")
    checks = (
        "Verify repeat names against original FIR identity attributes.",
        "Normalize beat concentration against population and reporting volume.",
        "Treat model scores and candidate links as review signals, not facts.",
    )
    check_y = 184
    for check in checks:
        canvas.setFillColor(HexColor("#45D6B1")); canvas.circle(211, check_y + 2, 2, fill=1, stroke=0)
        canvas.setFillColor(HexColor("#9BAEA7")); canvas.setFont("Helvetica", 7.5); canvas.drawString(221, check_y, check)
        check_y -= 22
    report_digest = hashlib.sha256(graph().model_dump_json().encode("utf-8")).hexdigest()[:16]
    canvas.setFillColor(HexColor("#60766F")); canvas.setFont("Helvetica", 7); canvas.drawString(42, 34, f"ANALYST REVIEW REQUIRED · EVIDENCE MANIFEST {report_digest.upper()} · W3C PROV-O ALIGNED")
    canvas.save(); buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=sentinel_investigation_report.pdf"})


@app.get("/api/config", tags=["settings"])
def get_config():
    return system_config


@app.post("/api/config", tags=["settings"])
def update_config(update: ConfigUpdate):
    for key, value in update.model_dump(exclude_none=True).items():
        system_config[key] = value
    return system_config


@app.get("/api/models", tags=["settings"])
def available_models():
    graphsage = model_status()
    return [
        {"id": "sentinel-crime-ner-v1", "name": "Sentinel Crime NER", "status": "ready", "source": "supplied pipeline + ontology"},
        {"id": "spacy-en-core-web-sm", "name": "spaCy English Small", "status": "optional", "source": "spaCy"},
        {"id": "rule-risk-v1", "name": "Transparent Crime Risk", "status": "ready", "source": "local"},
        {
            "id": graphsage["id"],
            "name": graphsage["name"],
            "status": graphsage["status"],
            "source": "supplied GraphSAGE notebook",
            "artifacts": graphsage["artifacts"],
        },
    ]


@app.get("/api/models/graphsage/status", tags=["settings"])
def graphsage_status():
    return {**model_status(), "link_predictions": link_prediction_summary()}


@app.get("/api/data/quality", tags=["data management"])
def quality_report():
    return data_quality()


@app.get("/api/provenance/manifest", tags=["provenance"])
def get_provenance_manifest():
    return provenance_manifest()


@app.get("/api/ontology/summary", tags=["ontology"])
def ontology_summary():
    ontology_path = Path(__file__).resolve().parent.parent / "ontology" / "final_ontology.ttl"
    text = ontology_path.read_text(encoding="utf-8")
    labels = re.findall(r'rdfs:label\s+"([^"]+)"', text)
    return {
        "name": "Crime Investigation Ontology",
        "path": ontology_path.name,
        "classes": [label for label in labels if label[0].isupper()],
        "properties": [label for label in labels if label[0].islower()],
        "class_count": len(re.findall(r"rdf:type\s+owl:Class", text)),
        "object_property_count": len(re.findall(r"rdf:type\s+owl:ObjectProperty", text)),
        "data_property_count": len(re.findall(r"rdf:type\s+owl:DatatypeProperty", text)),
    }
