"""PostgreSQL durable state and optional case-scoped Neo4j graph mirroring.

Atomic local snapshots remain the execution and recovery layer. Hosted and
private profiles can durably mirror those artifacts into PostgreSQL; the hybrid
profile additionally mirrors graph topology into Neo4j.
"""

import hashlib
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from neo4j import GraphDatabase
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text, create_engine, delete, func, text, update
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from .config import get_settings
from .models import GraphEdge, GraphNode, GraphPayload, UploadRecord


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
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    source: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(64))
    source_sha256: Mapped[str] = mapped_column(String(64))
    owner: Mapped[str] = mapped_column(String(320), index=True)
    node_count: Mapped[int] = mapped_column(Integer, default=0)
    edge_count: Mapped[int] = mapped_column(Integer, default=0)
    graph_version: Mapped[str] = mapped_column(String(64), default="1")
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AlertRecord(Base):
    __tablename__ = "alerts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    investigation_id: Mapped[str | None] = mapped_column(ForeignKey("investigations.id"))
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


class DurableObject(Base):
    """Provider-neutral binary object store backed by PostgreSQL."""

    __tablename__ = "durable_objects"
    key: Mapped[str] = mapped_column(String(640), primary_key=True)
    content: Mapped[bytes] = mapped_column(LargeBinary)
    sha256: Mapped[str] = mapped_column(String(64))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Neo4jGraphRepository:
    """Batch-safe Neo4j adapter with indexed MERGE operations."""

    def __init__(self) -> None:
        settings = get_settings()
        self.driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))

    def close(self) -> None:
        self.driver.close()

    def ensure_schema(self) -> None:
        queries = [
            "DROP CONSTRAINT entity_id IF EXISTS",
            "CREATE CONSTRAINT entity_key IF NOT EXISTS FOR (e:Entity) REQUIRE e.key IS UNIQUE",
            "CREATE INDEX entity_investigation IF NOT EXISTS FOR (e:Entity) ON (e.investigation_id)",
            "CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)",
            "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type)",
            "CREATE INDEX entity_risk IF NOT EXISTS FOR (e:Entity) ON (e.risk)",
        ]
        with self.driver.session() as session:
            for query in queries:
                session.run(query).consume()

    def replace_graph(self, graph: GraphPayload, investigation_id: str = "default", batch_size: int = 1000) -> None:
        nodes = [
            {"key": f"{investigation_id}:{item.id}", "props": {**item.model_dump(), "entity_id": item.id, "investigation_id": investigation_id}}
            for item in graph.nodes
        ]
        edges = [
            {
                "key": f"{investigation_id}:{item.id}",
                "source_key": f"{investigation_id}:{item.source}",
                "target_key": f"{investigation_id}:{item.target}",
                "props": {**item.model_dump(), "edge_id": item.id, "investigation_id": investigation_id},
            }
            for item in graph.edges
        ]
        with self.driver.session() as session:
            session.run("MATCH (e:Entity {investigation_id: $investigation_id}) DETACH DELETE e", investigation_id=investigation_id).consume()
            for start in range(0, len(nodes), batch_size):
                session.run(
                    "UNWIND $rows AS row MERGE (e:Entity {key: row.key}) SET e += row.props, e.key = row.key",
                    rows=nodes[start : start + batch_size],
                ).consume()
            for start in range(0, len(edges), batch_size):
                session.run(
                    "UNWIND $rows AS row MATCH (a:Entity {key: row.source_key}), (b:Entity {key: row.target_key}) "
                    "MERGE (a)-[r:RELATES_TO {key: row.key}]->(b) SET r += row.props, r.key = row.key",
                    rows=edges[start : start + batch_size],
                ).consume()

    def subgraph(self, investigation_id: str = "default", limit: int = 1500) -> GraphPayload:
        with self.driver.session() as session:
            node_rows = session.run(
                "MATCH (n:Entity {investigation_id: $investigation_id}) RETURN properties(n) AS node LIMIT $limit",
                investigation_id=investigation_id,
                limit=limit,
            ).data()
            keys = [row["node"]["key"] for row in node_rows]
            edge_rows = session.run(
                "MATCH (a:Entity)-[r:RELATES_TO]->(b:Entity) WHERE a.key IN $keys AND b.key IN $keys RETURN properties(r) AS edge",
                keys=keys,
            ).data()
        node_values = [{key: value for key, value in row["node"].items() if key not in {"key", "entity_id", "investigation_id"}} for row in node_rows]
        edge_values = [{key: value for key, value in row["edge"].items() if key not in {"key", "edge_id", "investigation_id"}} for row in edge_rows]
        return GraphPayload(nodes=[GraphNode(**row) for row in node_values], edges=[GraphEdge(**row) for row in edge_values])


@lru_cache(maxsize=1)
def _engine():
    url = get_settings().database_url
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return create_engine(url, pool_pre_ping=True)


@lru_cache(maxsize=1)
def _session_factory() -> sessionmaker[Session]:
    return sessionmaker(_engine(), expire_on_commit=False)


def initialize_persistence() -> None:
    Base.metadata.create_all(_engine())
    if get_settings().persistence_mode == "hybrid":
        repository = Neo4jGraphRepository()
        try:
            repository.ensure_schema()
        finally:
            repository.close()


def _state_key(path: Path) -> str:
    settings = get_settings()
    resolved = path.resolve()
    exact = [
        (settings.audit_path.resolve(), "audit/log"),
        (settings.decisions_path.resolve(), "decisions/state"),
    ]
    for candidate, key in exact:
        if resolved == candidate:
            return key
    directories = [
        (settings.audit_anchor_dir.resolve(), "anchors"),
        (settings.upload_dir.resolve(), "uploads"),
        (settings.investigation_dir.resolve(), "investigations"),
    ]
    for root, namespace in directories:
        if resolved == root or root in resolved.parents:
            relative = resolved.relative_to(root).as_posix()
            return f"{namespace}/{relative}"
    raise ValueError(f"Path is outside the configured durable-state roots: {path}")


def _path_for_state_key(key: str) -> Path:
    settings = get_settings()
    if key == "audit/log":
        return settings.audit_path
    if key == "decisions/state":
        return settings.decisions_path
    roots = {
        "anchors": settings.audit_anchor_dir,
        "uploads": settings.upload_dir,
        "investigations": settings.investigation_dir,
    }
    namespace, separator, relative = key.partition("/")
    if not separator or namespace not in roots or not relative:
        raise ValueError(f"Invalid durable-state key: {key}")
    root = roots[namespace].resolve()
    target = (root / relative).resolve()
    if root not in target.parents:
        raise ValueError(f"Durable-state key escapes its configured root: {key}")
    return target


def persist_state_path(path: Path) -> None:
    """Mirror one completed local artifact into PostgreSQL."""
    if get_settings().persistence_mode == "local":
        return
    content = path.read_bytes()
    key = _state_key(path)
    with _session_factory()() as session:
        record = session.get(DurableObject, key) or DurableObject(key=key)
        record.content = content
        record.sha256 = hashlib.sha256(content).hexdigest()
        session.add(record)
        session.commit()


def delete_state_path(path: Path) -> None:
    if get_settings().persistence_mode == "local":
        return
    with _session_factory()() as session:
        session.execute(delete(DurableObject).where(DurableObject.key == _state_key(path)))
        session.commit()


def restore_state_objects() -> int:
    """Restore PostgreSQL objects before the application reads local snapshots."""
    if get_settings().persistence_mode == "local":
        return 0
    restored = 0
    with _session_factory()() as session:
        rows = session.query(DurableObject).order_by(DurableObject.key).all()
        for row in rows:
            content = bytes(row.content)
            if hashlib.sha256(content).hexdigest() != row.sha256:
                raise RuntimeError(f"Durable-state digest mismatch: {row.key}")
            target = _path_for_state_key(row.key)
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(f".{target.name}.restore.tmp")
            temporary.write_bytes(content)
            temporary.replace(target)
            restored += 1
    return restored


def durable_object_count() -> int:
    with _session_factory()() as session:
        return int(session.query(DurableObject).count())


def persist_investigation(entry: dict[str, Any], graph: GraphPayload) -> None:
    if get_settings().persistence_mode == "hybrid":
        repository = Neo4jGraphRepository()
        try:
            repository.replace_graph(graph, entry["id"])
        finally:
            repository.close()
    with _session_factory()() as session:
        record = session.get(Investigation, entry["id"]) or Investigation(id=entry["id"])
        record.name = entry["name"]
        record.source = entry["source"]
        record.source_type = entry["source_type"]
        record.source_sha256 = entry["source_sha256"]
        record.owner = entry.get("owner", "local-analyst")
        record.node_count = int(entry.get("nodes", len(graph.nodes)))
        record.edge_count = int(entry.get("edges", len(graph.edges)))
        record.active = bool(entry.get("active"))
        record.details = {"classification": entry.get("classification"), "access_scope": entry.get("access_scope")}
        session.add(record)
        session.commit()


def set_persisted_active(investigation_id: str) -> None:
    with _session_factory()() as session:
        session.execute(update(Investigation).values(active=False))
        record = session.get(Investigation, investigation_id)
        if record:
            record.active = True
        session.commit()


def delete_persisted_investigation(investigation_id: str) -> None:
    if get_settings().persistence_mode == "hybrid":
        repository = Neo4jGraphRepository()
        try:
            with repository.driver.session() as neo_session:
                neo_session.run("MATCH (e:Entity {investigation_id: $investigation_id}) DETACH DELETE e", investigation_id=investigation_id).consume()
        finally:
            repository.close()
    with _session_factory()() as session:
        record = session.get(Investigation, investigation_id)
        if record:
            session.delete(record)
            session.commit()


def persistence_health() -> dict[str, bool]:
    with _session_factory()() as session:
        session.execute(text("SELECT 1"))
    result = {"postgresql": True}
    if get_settings().persistence_mode == "hybrid":
        repository = Neo4jGraphRepository()
        try:
            with repository.driver.session() as neo_session:
                neo_session.run("RETURN 1 AS ok").consume()
        finally:
            repository.close()
        result["neo4j"] = True
    return result


def persist_upload(upload: UploadRecord, actor_email: str, actor_role: str = "analyst") -> None:
    with _session_factory()() as session:
        user = session.query(User).filter(User.email == actor_email).one_or_none()
        if user is None:
            user = User(email=actor_email, password_hash="external-config", role=actor_role, is_active=True)
            session.add(user)
            session.flush()
        record = session.get(Upload, upload.id) or Upload(id=upload.id)
        record.filename = upload.filename
        record.size = upload.size
        record.status = upload.status
        record.records = upload.records
        record.created_at = upload.created_at
        record.user_id = user.id
        session.add(record)
        session.commit()


def update_persisted_upload(upload: UploadRecord) -> None:
    with _session_factory()() as session:
        record = session.get(Upload, upload.id)
        if record:
            record.status = upload.status
            record.records = upload.records
            session.commit()


def load_persisted_uploads() -> list[UploadRecord]:
    with _session_factory()() as session:
        rows = session.query(Upload).order_by(Upload.created_at.desc()).all()
        return [
            UploadRecord(
                id=row.id,
                filename=row.filename,
                size=row.size,
                status=row.status,
                records=row.records,
                created_at=row.created_at,
            )
            for row in rows
        ]


def delete_persisted_upload(upload_id: str) -> None:
    with _session_factory()() as session:
        record = session.get(Upload, upload_id)
        if record:
            session.delete(record)
            session.commit()
