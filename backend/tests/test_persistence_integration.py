"""Real PostgreSQL + Neo4j integration proof, enabled by the CI service job."""

from __future__ import annotations

import os

import pytest


pytestmark = pytest.mark.skipif(
    os.getenv("SENTINEL_RUN_HYBRID_INTEGRATION") != "1",
    reason="requires the PostgreSQL and Neo4j integration services",
)


def test_hybrid_persistence_is_durable_and_case_isolated():
    from app.database import (
        Neo4jGraphRepository,
        delete_persisted_investigation,
        initialize_persistence,
        persist_investigation,
        persistence_health,
        set_persisted_active,
    )
    from app.models import GraphEdge, GraphNode, GraphPayload

    initialize_persistence()
    first_id, second_id = "ci-hybrid-case-a", "ci-hybrid-case-b"
    for investigation_id in (first_id, second_id):
        delete_persisted_investigation(investigation_id)

    def payload(name: str, source_record: str) -> GraphPayload:
        return GraphPayload(
            nodes=[
                GraphNode(id="shared-local-id", name=name, type="person", risk=40, confidence=90, community=1),
                GraphNode(id="event-1", name=f"Evidence for {name}", type="event", risk=40, confidence=90, community=1),
            ],
            edges=[
                GraphEdge(
                    id="edge-1",
                    source="event-1",
                    target="shared-local-id",
                    label="MENTIONS_PERSON",
                    confidence=90,
                    evidence_record_ids=[source_record],
                    evidence_hashes=["b" * 64],
                    source_types=["FIR"],
                    observed_at="2026-09-04T10:00:00",
                )
            ],
        )

    def entry(investigation_id: str, name: str) -> dict[str, object]:
        return {
            "id": investigation_id,
            "name": name,
            "source": f"{investigation_id}.json",
            "source_type": "CI FIXTURE",
            "source_sha256": "a" * 64,
            "owner": "ci@sentinel.local",
            "active": False,
            "classification": "synthetic-ci-only",
            "access_scope": "case-owner",
        }

    try:
        persist_investigation(entry(first_id, "Case A"), payload("Case A Subject", "FIR-CI-A"))
        persist_investigation(entry(second_id, "Case B"), payload("Case B Subject", "FIR-CI-B"))
        set_persisted_active(second_id)
        assert persistence_health() == {"postgresql": True, "neo4j": True}

        repository = Neo4jGraphRepository()
        try:
            first = repository.subgraph(first_id)
            second = repository.subgraph(second_id)
        finally:
            repository.close()

        assert {node.name for node in first.nodes} == {"Case A Subject", "Evidence for Case A Subject"}
        assert {node.name for node in second.nodes} == {"Case B Subject", "Evidence for Case B Subject"}
        assert first.edges[0].evidence_record_ids == ["FIR-CI-A"]
        assert second.edges[0].evidence_record_ids == ["FIR-CI-B"]
    finally:
        for investigation_id in (first_id, second_id):
            delete_persisted_investigation(investigation_id)
