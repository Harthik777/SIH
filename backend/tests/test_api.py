import pytest
from fastapi.testclient import TestClient

from app import audit_anchor, audit_log, main as main_module, suraksha
from app.main import app
from app.crime_pipeline import build_graph, load_crime_graph, parse_fir
from app.graphsage import INPUT_FEATURES, analyze_graph, build_features
from app.operations import SlidingWindowRateLimiter
from app.security import hash_password


client = TestClient(app)


@pytest.fixture(autouse=True)
def begin_each_test_with_validation_corpus():
    """Keep tests deterministic even when the live demo is left on Operation Suraksha."""
    assert client.post("/api/investigations/city-shield/activate").status_code == 200
    yield


def test_health_reports_loaded_crime_graph():
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["entities"] > 1000
    assert payload["relationships"] > 1000
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


def test_local_login_rejects_arbitrary_credentials():
    rejected = client.post("/api/auth/login", json={"email": "anyone@example.com", "password": "anything"})
    assert rejected.status_code == 401
    accepted = client.post("/api/auth/login", json={"email": "analyst@sentinel.local", "password": "sentinel-demo"})
    assert accepted.status_code == 200
    assert accepted.json()["security_mode"] in {"demo", "configured"}


def test_public_showcase_disables_credential_login(monkeypatch):
    monkeypatch.setattr(main_module.settings, "public_demo", True)
    response = client.post("/api/auth/login", json={"email": "supervisor@sentinel.local", "password": "sentinel-supervisor"})
    assert response.status_code == 403
    assert "no credentials are required" in response.json()["detail"]
    stale = client.get("/api/auth/me", headers={"Authorization": "Bearer expired-private-session"})
    assert stale.status_code == 200
    assert stale.json() == {"email": "public-demo@sentinel.local", "role": "demo", "mode": "synthetic-public-demo"}


def test_graph_search_finds_real_dataset_entity():
    response = client.post("/api/graph/search", json={"query": "Deandre Allen"})
    assert response.status_code == 200
    items = response.json()["items"]
    assert items[0]["name"] == "Deandre Allen"
    assert items[0]["type"] == "person"


def test_ontology_summary_matches_supplied_schema():
    response = client.get("/api/ontology/summary")
    assert response.status_code == 200
    payload = response.json()
    assert "CrimeIncident" in payload["classes"]
    assert "hasSuspect" in payload["properties"]


def test_graphml_export_is_downloadable():
    response = client.get("/api/export/graph/graphml")
    assert response.status_code == 200
    assert "<graphml" in response.text
    assert "attachment" in response.headers["content-disposition"]


def test_stix_export_is_interoperable_receipted_and_privacy_aware():
    try:
        assert client.post("/api/investigations/operation-suraksha/activate").status_code == 200
        graph = client.get("/api/visualization/graph").json()
        response = client.get("/api/export/graph/stix")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/stix+json")
        assert "attachment" in response.headers["content-disposition"]

        bundle = response.json()
        assert bundle["type"] == "bundle"
        assert bundle["id"].startswith("bundle--")
        objects = bundle["objects"]
        object_ids = {item["id"] for item in objects}
        relationships = [item for item in objects if item["type"] == "relationship"]
        assert len(relationships) == len(graph["edges"])
        assert all(item["spec_version"] == "2.1" for item in objects)
        assert all(item["source_ref"] in object_ids and item["target_ref"] in object_ids for item in relationships)
        assert all(item["x_sentinel_epistemic_status"] in {"observed", "derived"} for item in relationships)

        protected = [item for item in objects if item.get("x_sentinel_protected")]
        assert len(protected) == 2
        assert all(item["type"] == "identity" and item["identity_class"] == "individual" for item in protected)
        assert all("x_sentinel_risk_indicator" not in item and "x_sentinel_aliases" not in item for item in protected)
        assert "Nandini" not in response.text and "Asha" not in response.text
        report = next(item for item in objects if item["type"] == "report")
        assert report["x_sentinel_classification"] == "synthetic-evaluation-only"
        assert len(report["x_sentinel_graph_sha256"]) == 64
    finally:
        assert client.post("/api/investigations/city-shield/activate").status_code == 200


def test_fir_without_plate_never_creates_vehicle():
    report = (
        "On 03/05/2026 at approximately 21:30 hours, officers documented Case Number JC100339. "
        "An incident of ROBBERY involving ARMED: HANDGUN was reported at 6800XX N BROADWAY, "
        "situated in District 022, Beat 2213 (Ward 19, Community Area 72). The incident occurred "
        "on/at a ALLEY. The suspect, identified as Devon Wright, was implicated. NO ARREST was "
        "effected. Domestic dispute: NO. IUCR code 031A and FBI Code 03."
    )
    record = parse_fir(report)
    assert record["vehicle_plate"] is None
    normalized = {key: "" if value is None else str(value) for key, value in record.items()}
    payload = build_graph([normalized])
    assert not any(node.type == "vehicle" for node in payload.nodes)


def test_graphsage_features_match_notebook_schema():
    node_order, features, degrees = build_features(load_crime_graph())
    assert len(node_order) == 1530
    assert all(len(row) == INPUT_FEATURES for row in features)
    assert max(row[-1] for row in features) == 1.0
    assert max(degrees.values()) > 0


def test_graphsage_endpoint_reports_real_or_preview_mode_explicitly():
    response = client.get("/api/analytics/graphsage?limit=3")
    assert response.status_code == 200
    payload = response.json()
    assert payload["model"]["architecture"]["input_features"] == 7
    training_summary = payload["model"]["training_summary"]
    assert training_summary["reported_reproduction_f1"] == 1.0
    assert "reported_final_validation_f1" not in training_summary
    assert "reproduction" in training_summary["metric_role"]
    if training_summary["reproduced_checkpoint"]:
        assert "reproduction_f1" in training_summary["reproduced_checkpoint"]
        assert "validation_f1" not in training_summary["reproduced_checkpoint"]
    assert len(payload["items"]) == 3
    artifacts = payload["model"]["artifacts"]
    if artifacts["checkpoint_available"] and (artifacts["runtime_available"] or artifacts["lightweight_runtime_available"]):
        assert payload["mode"] in {"graphsage-inference", "graphsage-lightweight-inference"}
        assert all(isinstance(item["probability"], float) for item in payload["items"])
    else:
        assert payload["mode"] == "structural-feature-preview"
        assert all(item["probability"] is None for item in payload["items"])


def test_supplied_link_prediction_artifact_is_served():
    status = client.get("/api/models/graphsage/status").json()
    assert status["link_predictions"]["rows"] == 50
    assert status["link_predictions"]["predicted_links"] == 0
    response = client.get("/api/analysis/link-predictions?limit=2")
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["probability"] == 0.3259


def test_briefing_exposes_quality_provenance_and_guardrails():
    response = client.get("/api/analysis/briefing")
    assert response.status_code == 200
    payload = response.json()
    assert payload["operating_mode"] == "local-single-machine"
    assert payload["quality"]["required_field_completeness"] == 100.0
    assert payload["quality"]["duplicate_case_numbers"] == 0
    assert payload["provenance"]["verified"] == payload["provenance"]["total"]
    assert len(payload["findings"]) >= 3
    assert any("human" in item.lower() for item in payload["guardrails"])


def test_provenance_manifest_contains_verifiable_sha256_hashes():
    payload = client.get("/api/provenance/manifest").json()
    assert payload["offline_capable"] is True
    assert payload["external_services_required"] is False
    assert all(len(source["sha256"]) == 64 for source in payload["sources"])


def test_transparent_link_candidates_expose_supporting_signals():
    payload = client.get("/api/analysis/link-candidates?limit=3").json()
    assert payload["status"] == "hypothesis-only"
    assert len(payload["items"]) == 3
    assert all(len(item["signals"]) >= 2 for item in payload["items"])
    assert all(item["method"] == "explainable-feature-overlap-v1" for item in payload["items"])


def test_upload_pipeline_profiles_real_content_and_builds_graph():
    csv_body = (
        "case_number,suspect_name,vehicle_plate,date,year,primary_type,description,block,location_description,district,beat,ward,community_area,iucr,fbi_code,arrest,domestic\n"
        "ZZ000001,Test Person,,2026-09-04 10:00:00,2026,THEFT,OVER $500,100 TEST ST,STREET,001,0111,1,1,0810,06,false,false\n"
        "ZZ000002,Test Person,KA-0001-ZZ,2026-09-04 11:00:00,2026,ROBBERY,ARMED,200 TEST ST,ALLEY,001,0111,1,1,031A,03,false,false\n"
    )
    uploaded = client.post("/api/upload", files={"file": ("test_cases.csv", csv_body, "text/csv")}).json()
    started = client.post("/api/pipeline/start", json={"upload_id": uploaded["id"], "activate": False}).json()
    state = client.get(f"/api/pipeline/status/{started['pipeline_id']}").json()
    assert state["status"] == "complete"
    assert state["result"]["source"]["records"] == 2
    assert state["result"]["graph"]["nodes"] > 0
    assert state["result"]["graph"]["edges"] > 0
    assert len(state["result"]["provenance"]["digest"]) == 64
    assert state["result"]["investigation"]["active"] is False
    assert client.delete(f"/api/investigations/{state['result']['investigation']['id']}").status_code == 204
    assert client.delete(f"/api/upload/{uploaded['id']}").status_code == 204


def test_active_dataset_drives_timeline_locations_alerts_and_structure():
    graph = client.get("/api/visualization/graph").json()
    timeline = client.get("/api/visualization/timeline").json()
    locations = client.get("/api/visualization/locations").json()
    alerts = client.get("/api/alerts").json()
    distribution = client.get("/api/analytics/distribution").json()
    centrality = client.get("/api/analytics/centrality?metric=influence&limit=5").json()
    individuals = client.get("/api/analytics/key-individuals?limit=5").json()

    node_ids = {node["id"] for node in graph["nodes"]}
    assert timeline and all(event["case_id"] in node_ids for event in timeline)
    assert locations and locations[0]["count"] == 35
    assert all("not source GPS" in item["coordinate_basis"] for item in locations)
    assert alerts and all(alert["entityId"] in node_ids for alert in alerts)
    assert distribution["structure"]["nodes"] == len(graph["nodes"])
    assert distribution["degree_distribution"]
    assert [item["rank"] for item in centrality] == [1, 2, 3, 4, 5]
    assert all(item["method"] for item in centrality)
    assert all(item["node"]["type"] == "person" for item in individuals["items"])
    assert "not a finding of guilt" in individuals["definition"]


def test_investigation_workspace_has_durable_default():
    assert client.post("/api/investigations/city-shield/activate").status_code == 200
    workspace = client.get("/api/investigations").json()
    assert workspace["active_id"] == "city-shield"
    assert workspace["persistence"] == "local-json-atomic"
    assert any(item["id"] == "city-shield" and item["built_in"] for item in workspace["items"])


def test_trace_outputs_are_proof_carrying_and_reproducible():
    graph = client.get("/api/visualization/graph").json()
    nodes = {node["id"]: node for node in graph["nodes"]}
    person_id = next(node_id for node_id, node in nodes.items() if node["type"] == "person")
    adjacent_edges = [edge for edge in graph["edges"] if person_id in {edge["source"], edge["target"]}]
    event_id = next(
        (edge["target"] if edge["source"] == person_id else edge["source"])
        for edge in adjacent_edges
        if nodes[edge["target"] if edge["source"] == person_id else edge["source"]]["type"] == "event"
    )
    crime_id = next(
        (edge["target"] if edge["source"] == event_id else edge["source"])
        for edge in graph["edges"]
        if event_id in {edge["source"], edge["target"]}
        and nodes[edge["target"] if edge["source"] == event_id else edge["source"]]["type"] == "crime"
    )

    path = client.get("/api/analysis/connection-path", params={"source_id": person_id, "target_id": crime_id}).json()
    assert path["found"] is True
    assert path["hops"] == 2
    assert all(step["evidence_status"] == "stored-observation" for step in path["steps"])
    assert len(path["receipt"]) == 64

    counterfactual = client.get(f"/api/analysis/counterfactual/{person_id}").json()
    trace = client.get(f"/api/analysis/trace/{person_id}").json()
    motifs = client.get("/api/analysis/motifs?limit=10").json()
    assert counterfactual["scenarios"] and len(counterfactual["receipt"]) == 64
    assert trace["neighborhood"] and len(trace["receipt"]) == 64
    assert motifs["items"] and len(motifs["receipt"]) == 64
    assert all(len(item["receipt"]) == 64 and item["alternative"] for item in motifs["items"])


def test_generic_cdr_and_financial_fields_create_auditable_graph():
    payload = build_graph(
        [
            {
                "call_id": "CALL-01",
                "timestamp": "2026-09-04 10:00:00",
                "caller_number": "+91 90000 00001",
                "callee_number": "+91 90000 00002",
                "caller_name": "Review Subject",
                "tower_location": "Sector 12",
            },
            {
                "transaction_id": "TX-02",
                "timestamp": "2026-09-04 11:00:00",
                "source_account": "AC-100",
                "destination_account": "AC-200",
                "amount": "125000",
                "organization": "Example Trading",
            },
        ]
    )
    assert {node.type for node in payload.nodes} >= {"event", "person", "phone", "account", "organization", "location"}
    assert any(edge.label == "CALLED" for edge in payload.edges)
    assert any(edge.label == "TRANSFERRED_TO" for edge in payload.edges)
    analysis = analyze_graph(payload, 5)
    assert analysis["mode"] == "schema-incompatible-preview"
    assert all(item["probability"] is None for item in analysis["items"])


def test_compatible_upload_can_become_active_investigation():
    csv_body = (
        "call_id,timestamp,caller_number,callee_number,caller_name,tower_location\n"
        "CALL-99,2026-09-04 12:00:00,+919000000001,+919000000002,Test Analyst Subject,Sector 12\n"
    )
    uploaded = client.post("/api/upload", files={"file": ("cdr.csv", csv_body, "text/csv")}).json()
    started = client.post("/api/pipeline/start", json={"upload_id": uploaded["id"], "activate": True}).json()
    state = client.get(f"/api/pipeline/status/{started['pipeline_id']}").json()
    investigation_id = state["result"]["investigation"]["id"]
    assert state["result"]["investigation"]["active"] is True
    assert client.get("/api/investigations").json()["active_id"] == investigation_id
    assert "phone" in {node["type"] for node in client.get("/api/visualization/graph").json()["nodes"]}
    assert client.get("/api/analytics/graphsage").json()["mode"] == "schema-incompatible-preview"
    assert client.get("/api/analysis/link-candidates").json()["total"] == 0
    assert client.get("/api/analysis/briefing").json()["model"]["status"] == "schema-review"
    assert len(client.get("/api/visualization/timeline").json()) == 1
    assert len(client.get("/api/visualization/locations").json()) == 1
    assert client.post("/api/investigations/city-shield/activate").status_code == 200
    assert client.delete(f"/api/investigations/{investigation_id}").status_code == 204
    assert client.delete(f"/api/upload/{uploaded['id']}").status_code == 204


def test_suraksha_replay_and_ground_truth_are_complete_and_receipted():
    workspace = client.get("/api/investigations").json()
    suraksha_item = next(item for item in workspace["items"] if item["id"] == "operation-suraksha")
    assert suraksha_item["built_in"] is True
    assert suraksha_item["classification"] == "synthetic-evaluation-only"

    replay = client.get("/api/demo/suraksha/replay").json()
    evaluation = client.get("/api/demo/suraksha/evaluation").json()
    assert replay["source_counts"] == {"ANPR": 4, "BANK": 7, "CDR": 10, "FIR": 6, "OSINT": 2, "SURVEILLANCE": 3}
    assert replay["records"] == 32
    assert replay["nodes"] == 64
    assert replay["edges"] == 148
    assert len(replay["steps"]) == 6
    assert len(replay["receipt"]) == 64
    assert all(len(step["receipt"]) == 64 and step["evidence_ids"] for step in replay["steps"])
    assert evaluation["summary"] == {
        "entities_recovered": 14,
        "entities_expected": 14,
        "relationships_recovered": 6,
        "relationships_expected": 6,
        "hidden_path_recovered": True,
        "false_merges": 0,
        "processing_mode": "deterministic-local",
    }
    assert evaluation["negative_identity_control"]["distinct_nodes_preserved"] is True
    assert len(evaluation["expected_path"]["trace_receipt"]) == 64
    assert len(evaluation["receipt"]) == 64


def test_suraksha_fusion_patterns_are_computed_and_source_provenanced():
    assurance = client.get("/api/demo/suraksha/fusion-assurance").json()
    assert assurance["summary"] == {
        "checks_passed": 5,
        "checks_total": 5,
        "patterns_recovered": 5,
        "patterns_expected": 5,
        "edge_provenance_coverage": 100.0,
        "source_channels": 6,
    }
    patterns = {item["id"]: item for item in assurance["patterns"]}
    assert set(patterns) == {
        "communication-burst",
        "rapid-split-transfer",
        "circular-fund-flow",
        "cross-source-convergence",
        "cross-channel-bridge",
    }
    assert patterns["cross-source-convergence"]["source_types"] == ["ANPR", "CDR", "SURVEILLANCE"]
    assert set(patterns["circular-fund-flow"]["evidence_record_ids"]) >= {"TX-S-001", "TX-S-003", "TX-S-004"}
    assert all(item["alternative"] and item["analyst_action"] and len(item["receipt"]) == 64 for item in patterns.values())
    assert len(assurance["receipt"]) == 64


def test_suraksha_temporal_emergence_reconstructs_network_growth():
    emergence = client.get("/api/demo/suraksha/emergence").json()
    snapshots = emergence["snapshots"]
    assert snapshots[0]["date"] == "2026-08-17"
    assert snapshots[-1]["cumulative_records"] == 32
    assert snapshots[-1]["cumulative_nodes"] == 64
    assert snapshots[-1]["cumulative_edges"] == 148
    assert snapshots[-1]["patterns_detected"] == 5
    assert any("circular-fund-flow" in snapshot["new_patterns"] for snapshot in snapshots)
    assert len(emergence["receipt"]) == 64


def test_suraksha_graph_edges_carry_record_level_provenance():
    try:
        assert client.post("/api/investigations/operation-suraksha/activate").status_code == 200
        edges = client.get("/api/visualization/graph").json()["edges"]
        assert len(edges) == 148
        assert all(edge["evidence_record_ids"] and edge["evidence_hashes"] and edge["source_types"] for edge in edges)
        assert all(all(len(value) == 64 for value in edge["evidence_hashes"]) for edge in edges)
        assert {source for edge in edges for source in edge["source_types"]} == {"FIR", "CDR", "BANK", "ANPR", "SURVEILLANCE", "OSINT"}
        subject = next(node for node in client.get("/api/visualization/graph").json()["nodes"] if node["name"] == "Subject A-17")
        coordinator = next(node for node in client.get("/api/visualization/graph").json()["nodes"] if node["name"] == "Coordinator C-04")
        path = client.get("/api/analysis/connection-path", params={"source_id": subject["id"], "target_id": coordinator["id"]}).json()
        assert all(step["evidence_record_ids"] and step["source_types"] for step in path["steps"])
    finally:
        assert client.post("/api/investigations/city-shield/activate").status_code == 200


def test_suraksha_identity_resolution_requires_a_human_safe_decision(monkeypatch, tmp_path):
    monkeypatch.setattr(suraksha, "DECISIONS_PATH", tmp_path / "resolution_decisions.json")
    candidate = client.get("/api/entity-resolution/candidates").json()["items"][0]
    assert candidate["recommendation"] == "keep-separate"
    assert candidate["left"]["id"] != candidate["right"]["id"]
    assert candidate["status"] == "pending-review"
    assert len(candidate["conflicting_signals"]) >= 3

    decision = client.post(
        f"/api/entity-resolution/{candidate['id']}/decision",
        json={
            "decision": "keep-separate",
            "rationale": "Distinct phone identifiers and incompatible locations require separate identities.",
        },
    )
    assert decision.status_code == 200
    assert decision.json()["effect"] == "Identity nodes remain separate"
    assert len(decision.json()["receipt"]) == 64
    reviewed = client.get("/api/entity-resolution/candidates").json()["items"][0]
    assert reviewed["status"] == "keep-separate"
    assert reviewed["decision"]["rationale"].startswith("Distinct phone")


def test_suraksha_can_drive_the_full_workspace_without_overclaiming():
    try:
        assert client.post("/api/investigations/operation-suraksha/activate").status_code == 200
        graph = client.get("/api/visualization/graph").json()
        briefing = client.get("/api/analysis/briefing").json()
        locations = client.get("/api/visualization/locations").json()
        model = client.get("/api/analytics/graphsage?limit=5").json()
        node_types = {node["type"] for node in graph["nodes"]}

        assert len(graph["nodes"]) == 64
        assert len(graph["edges"]) == 148
        assert node_types >= {"person", "protected_person", "phone", "account", "organization", "vehicle", "location", "event"}
        protected = [node for node in graph["nodes"] if node["type"] == "protected_person"]
        assert len(protected) == 2
        assert all(node["risk"] == 0 and "risk-scoring-prohibited" in node["tags"] for node in protected)
        assert briefing["quality"]["quality_gate"] == "pass"
        assert briefing["model"]["status"] == "schema-review"
        assert model["mode"] == "schema-incompatible-preview"
        assert locations and all("not source GPS" in item["coordinate_basis"] for item in locations)
        assert all(12.7 <= item["lat"] <= 13.2 and 77.3 <= item["lng"] <= 77.9 for item in locations)
        assert any("human" in item.lower() for item in briefing["guardrails"])
    finally:
        assert client.post("/api/investigations/city-shield/activate").status_code == 200


def test_protected_people_are_masked_and_reveal_is_audited(monkeypatch, tmp_path):
    monkeypatch.setattr(audit_log, "AUDIT_PATH", tmp_path / "audit_chain.jsonl")
    response = client.get("/api/protected-persons")
    assert response.status_code == 200
    profiles = response.json()["items"]
    assert profiles and all(item["status"] == "masked" and item["risk_scoring"] == "prohibited" for item in profiles)
    assert all("Nandini" not in item["name"] and "Asha" not in item["name"] for item in profiles)

    invalid = client.post(
        f"/api/protected-persons/{profiles[0]['id']}/reveal",
        json={"reason": "short", "authorization_reference": "D"},
    )
    assert invalid.status_code == 422
    revealed = client.post(
        f"/api/protected-persons/{profiles[0]['id']}/reveal",
        json={"reason": "Authorized verification during synthetic demonstration", "authorization_reference": "DEMO-001"},
    )
    assert revealed.status_code == 200
    assert revealed.json()["synthetic"] is True
    assert len(revealed.json()["audit_hash"]) == 64
    verified = client.get("/api/audit/verify").json()
    assert verified["valid"] is True and verified["entries"] == 1


def test_audit_chain_detects_tampering(monkeypatch, tmp_path):
    audit_path = tmp_path / "audit_chain.jsonl"
    monkeypatch.setattr(audit_log, "AUDIT_PATH", audit_path)
    audit_log.append_audit_event("test.action", "A")
    audit_log.append_audit_event("test.action", "B")
    assert audit_log.verify_audit_chain()["valid"] is True
    audit_path.write_text(audit_path.read_text(encoding="utf-8").replace('"target":"A"', '"target":"X"', 1), encoding="utf-8")
    verification = audit_log.verify_audit_chain()
    assert verification["valid"] is False
    assert any(error["reason"] == "content hash mismatch" for error in verification["errors"])


def test_external_checkpoint_is_blinded_bounded_and_downloadable(monkeypatch, tmp_path):
    monkeypatch.setattr(audit_log, "AUDIT_PATH", tmp_path / "audit_chain.jsonl")
    monkeypatch.setattr(main_module.settings, "audit_anchor_dir", tmp_path / "anchors")
    monkeypatch.setattr(main_module.settings, "connectivity_mode", "hybrid")
    monkeypatch.setattr(main_module.settings, "audit_anchor_mode", "opentimestamps")
    monkeypatch.setattr(main_module.settings, "public_demo", True)
    monkeypatch.setattr(main_module.settings, "audit_anchor_public_limit", 1)

    def fake_submit(checkpoint_path, proof_path, calendar_urls, timeout):
        assert b"protected_person" not in checkpoint_path.read_bytes()
        audit_anchor._atomic_write(proof_path, b"synthetic-ots-proof")
        return "f" * 64, [calendar_urls[0]]

    monkeypatch.setattr(audit_anchor, "_submit_proof", fake_submit)
    audit_log.append_audit_event("synthetic.case.open", "operation-suraksha", actor="test-supervisor")

    response = client.post("/api/audit/anchors", json={"submit": True})
    assert response.status_code == 200
    record = response.json()
    assert record["status"] == "calendar-pending"
    assert record["calendar_commitment"] == "f" * 64
    assert record["audit_head"] != client.get("/api/audit/verify").json()["head"]
    assert client.get(f"/api/audit/anchors/{record['id']}/proof").content == b"synthetic-ots-proof"
    bundle = client.get(f"/api/audit/anchors/{record['id']}/bundle")
    assert bundle.status_code == 200 and bundle.headers["content-type"] == "application/zip"
    checkpoint = client.get(f"/api/audit/anchors/{record['id']}/checkpoint").json()
    assert set(checkpoint) == {"schema", "created_at", "audit_method", "audit_entries", "audit_head"}
    assert client.post("/api/audit/anchors", json={"submit": True}).status_code == 429


def test_reset_restores_flagship_stage_and_clears_identity_decision(monkeypatch, tmp_path):
    monkeypatch.setattr(suraksha, "DECISIONS_PATH", tmp_path / "resolution_decisions.json")
    monkeypatch.setattr(audit_log, "AUDIT_PATH", tmp_path / "audit_chain.jsonl")
    candidate = client.get("/api/entity-resolution/candidates").json()["items"][0]
    client.post(
        f"/api/entity-resolution/{candidate['id']}/decision",
        json={"decision": "keep-separate", "rationale": "Conflicting immutable identifiers require separation."},
    )
    reset = client.post("/api/demo/suraksha/reset")
    assert reset.status_code == 200
    assert reset.json()["stage"] == 1
    assert reset.json()["cleared_identity_decisions"] == 1
    assert client.get("/api/entity-resolution/candidates").json()["items"][0]["status"] == "pending-review"


def test_readiness_and_scale_evidence_are_machine_readable():
    readiness = client.get("/api/system/readiness").json()
    assert readiness["ready"] is True
    assert readiness["offline_capable"] is True
    assert readiness["external_services_required"] is False
    benchmark = client.get("/api/benchmarks/scale").json()
    assert [run["records"] for run in benchmark["runs"]] == [10_000, 100_000]
    assert all(run["graph_build_seconds"] > 0 and run["peak_python_memory_mib"] > 0 for run in benchmark["runs"])
    assert benchmark["entity_resolution_safety"]["false_merge_rate"] == 0


def test_required_authentication_and_role_separation(monkeypatch, tmp_path):
    monkeypatch.setattr(main_module.settings, "auth_mode", "required")
    monkeypatch.setattr(audit_log, "AUDIT_PATH", tmp_path / "audit_chain.jsonl")
    assert client.get("/api/visualization/graph").status_code == 401

    analyst_login = client.post(
        "/api/auth/login",
        json={"email": "analyst@sentinel.local", "password": "sentinel-demo"},
    )
    analyst_header = {"Authorization": f"Bearer {analyst_login.json()['access_token']}"}
    assert client.get("/api/auth/me", headers=analyst_header).json()["role"] == "analyst"
    protected_id = client.get("/api/protected-persons", headers=analyst_header).json()["items"][0]["id"]
    assert client.post(
        f"/api/protected-persons/{protected_id}/reveal",
        headers=analyst_header,
        json={"reason": "Authorized synthetic case verification", "authorization_reference": "TEST-ROLE-1"},
    ).status_code == 403

    supervisor_login = client.post(
        "/api/auth/login",
        json={"email": "supervisor@sentinel.local", "password": "sentinel-supervisor"},
    )
    supervisor_header = {"Authorization": f"Bearer {supervisor_login.json()['access_token']}"}
    assert client.post(
        f"/api/protected-persons/{protected_id}/reveal",
        headers=supervisor_header,
        json={"reason": "Authorized synthetic case verification", "authorization_reference": "TEST-ROLE-2"},
    ).status_code == 200


def test_operational_endpoints_and_rate_limiter_are_machine_readable():
    assert client.get("/api/health/live").json() == {"status": "alive"}
    assert client.get("/api/health/ready").status_code == 200
    metrics = client.get("/api/system/metrics").json()
    assert metrics["requests_total"] > 0
    assert metrics["average_latency_ms"] >= 0
    prometheus = client.get("/metrics").text
    assert "sentinel_http_requests_total" in prometheus
    limiter = SlidingWindowRateLimiter()
    assert limiter.allow("test-client", 2)
    assert limiter.allow("test-client", 2)
    assert not limiter.allow("test-client", 2)


def test_password_hashing_and_binary_disguised_as_csv_are_guarded():
    assert hash_password("local-secret").startswith("pbkdf2_sha256$")
    uploaded = client.post(
        "/api/upload",
        files={"file": ("disguised.csv", b"MZ\x90\x00not-a-csv", "text/csv")},
    ).json()
    started = client.post("/api/pipeline/start", json={"upload_id": uploaded["id"], "activate": False}).json()
    state = client.get(f"/api/pipeline/status/{started['pipeline_id']}").json()
    assert state["status"] == "failed"
    assert "Executable or archive content" in state["error"]
    assert client.delete(f"/api/upload/{uploaded['id']}").status_code == 204


def test_model_evaluation_exposes_baselines_and_limitations():
    payload = client.get("/api/benchmarks/model").json()
    assert payload["schema_version"] == 2
    assert payload["dataset"]["suspects"] == 434
    reproduction = payload["graphsage"]["reproduction_diagnostic"]
    assert reproduction["full_supplied_graph"]["metrics"]["f1"] >= 0
    assert set(payload["fixed_baselines"]) == {"risk_score_at_least_70", "graph_degree_at_least_4"}
    selection_partition = reproduction["checkpoint_selection_partition"]
    assert selection_partition["samples"] == 87
    assert selection_partition["independent_outcome_labels"] is False
    assert selection_partition["used_for_checkpoint_selection"] is True
    stress = payload["graphsage"]["evidence_masking_stress_test"]
    assert stress["mask_rate"] == 0.2
    assert stress["trials"] == 10
    assert 0 < stress["summary"]["f1"]["mean"] < 1
    assert stress["generalization_claim_allowed"] is False
    assert payload["leakage_audit"]["status"] == "fails-independent-generalization-criteria"
    assert payload["claim_assurance"]["field_accuracy"] == "not-established"
    assert payload["claim_assurance"]["feature_target_dependency"] == "high"
    assert any("not independently adjudicated" in item for item in payload["limitations"])
