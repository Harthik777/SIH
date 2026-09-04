"""Provider-neutral tests for the hosted durable-state adapter."""

from pathlib import Path


def test_digest_verified_object_round_trip(tmp_path: Path):
    from app import database
    from app.config import get_settings

    settings = get_settings()
    original = {
        "persistence_mode": settings.persistence_mode,
        "database_url": settings.database_url,
        "upload_dir": settings.upload_dir,
        "investigation_dir": settings.investigation_dir,
        "audit_path": settings.audit_path,
        "audit_anchor_dir": settings.audit_anchor_dir,
        "decisions_path": settings.decisions_path,
    }
    settings.persistence_mode = "postgres"
    settings.database_url = f"sqlite:///{(tmp_path / 'durable.db').as_posix()}"
    settings.upload_dir = tmp_path / "uploads"
    settings.investigation_dir = tmp_path / "investigations"
    settings.audit_path = tmp_path / "audit" / "chain.jsonl"
    settings.audit_anchor_dir = tmp_path / "anchors"
    settings.decisions_path = tmp_path / "decisions" / "state.json"
    database._session_factory.cache_clear()
    database._engine.cache_clear()

    targets = {
        settings.investigation_dir / "case-1.json": b'{"case":"one","digest_verified":true}',
        settings.upload_dir / "upload-1.csv": b"case_id,subject\nFIR-1,Subject A\n",
        settings.audit_path: b'{"sequence":1,"hash":"test"}\n',
        settings.audit_anchor_dir / "checkpoint.ots": b"proof-bytes",
        settings.decisions_path: b'{"candidate":"keep-separate"}',
    }
    try:
        database.initialize_persistence()
        for target, content in targets.items():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            database.persist_state_path(target)
            target.unlink()

        assert database.restore_state_objects() == len(targets)
        for target, content in targets.items():
            assert target.read_bytes() == content
        assert database.durable_object_count() == len(targets)

        for target in targets:
            database.delete_state_path(target)
        assert database.durable_object_count() == 0
    finally:
        database._session_factory.cache_clear()
        database._engine.cache_clear()
        for key, value in original.items():
            setattr(settings, key, value)
