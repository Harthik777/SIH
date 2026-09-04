"""Production persistence adapters.

The API runs with an in-memory demo store by default. These models and repository
classes are the deployment seam used when PostgreSQL and Neo4j are enabled.
"""

from datetime import datetime
from typing import Any

from neo4j import GraphDatabase
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .config import get_settings
from .models import GraphEdge, GraphNode, GraphPayload


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="analyst")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Upload(Base):
    __tablename__ = "uploads"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    size: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), index=True)
    records: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class ProcessingLog(Base):
    __tablename__ = "processing_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    upload_id: Mapped[str] = mapped_column(ForeignKey("uploads.id"), index=True)
    stage: Mapped[str] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Investigation(Base):
    __tablename__ = "investigations"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    graph_version: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AlertRecord(Base):
    __tablename__ = "alerts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    investigation_id: Mapped[int | None] = mapped_column(ForeignKey("investigations.id"))
    anomaly_type: Mapped[str] = mapped_column(String(120))
    risk_score: Mapped[int] = mapped_column(Integer)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SavedFilter(Base):
    __tablename__ = "saved_filters"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(120))
    filter_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Neo4jGraphRepository:
    """Batch-safe Neo4j adapter with indexed MERGE operations."""

    def __init__(self) -> None:
        settings = get_settings()
        self.driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))

    def close(self) -> None:
        self.driver.close()

    def ensure_schema(self) -> None:
        queries = [
            "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
            "CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)",
            "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type)",
            "CREATE INDEX entity_risk IF NOT EXISTS FOR (e:Entity) ON (e.risk)",
        ]
        with self.driver.session() as session:
            for query in queries:
                session.run(query).consume()

    def replace_graph(self, graph: GraphPayload, batch_size: int = 1000) -> None:
        nodes = [item.model_dump() for item in graph.nodes]
        edges = [item.model_dump() for item in graph.edges]
        with self.driver.session() as session:
            for start in range(0, len(nodes), batch_size):
                session.run(
                    "UNWIND $rows AS row MERGE (e:Entity {id: row.id}) SET e += row",
                    rows=nodes[start : start + batch_size],
                ).consume()
            for start in range(0, len(edges), batch_size):
                session.run(
                    "UNWIND $rows AS row MATCH (a:Entity {id: row.source}), (b:Entity {id: row.target}) "
                    "MERGE (a)-[r:RELATES_TO {id: row.id}]->(b) SET r += row",
                    rows=edges[start : start + batch_size],
                ).consume()

    def subgraph(self, limit: int = 1500) -> GraphPayload:
        with self.driver.session() as session:
            node_rows = session.run("MATCH (n:Entity) RETURN properties(n) AS node LIMIT $limit", limit=limit).data()
            ids = [row["node"]["id"] for row in node_rows]
            edge_rows = session.run(
                "MATCH (a:Entity)-[r:RELATES_TO]->(b:Entity) WHERE a.id IN $ids AND b.id IN $ids RETURN properties(r) AS edge",
                ids=ids,
            ).data()
        return GraphPayload(nodes=[GraphNode(**row["node"]) for row in node_rows], edges=[GraphEdge(**row["edge"]) for row in edge_rows])

