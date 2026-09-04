from celery import Celery

from .config import get_settings


settings = get_settings()
celery = Celery("sentinel", broker=settings.redis_url, backend=settings.redis_url)
celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    worker_prefetch_multiplier=1,
)


@celery.task(name="sentinel.rebuild_graph")
def rebuild_graph() -> dict[str, int]:
    from .crime_pipeline import load_crime_graph
    load_crime_graph.cache_clear()
    graph = load_crime_graph()
    return {"nodes": len(graph.nodes), "edges": len(graph.edges)}

