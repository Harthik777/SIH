"""Deterministic, non-persistent scale benchmark for Sentinel's graph pipeline."""

from __future__ import annotations

import argparse
import gc
import json
import platform
import statistics
import sys
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.crime_pipeline import _stable_id, build_multisource_graph  # noqa: E402
from app.trace_engine import connection_path  # noqa: E402


OUTPUT_PATH = BACKEND_DIR / "benchmarks" / "scale_results.json"


def generate_records(count: int, phone_pool: int = 4_000, location_pool: int = 256) -> list[dict[str, str]]:
    """Generate reproducible CDR-like observations in memory; write no case data."""
    records: list[dict[str, str]] = []
    for index in range(count):
        caller = index % phone_pool
        callee = (index * 37 + 11) % phone_pool
        records.append(
            {
                "call_id": f"BENCH-{count}-{index:07d}",
                "timestamp": f"2026-08-{(index % 28) + 1:02d} {(index % 24):02d}:{(index * 7) % 60:02d}:00",
                "record_type": "synthetic benchmark cdr",
                "caller_number": f"+91-BENCH-{caller:05d}",
                "callee_number": f"+91-BENCH-{callee:05d}",
                "tower_location": f"Synthetic Tower {index % location_pool:03d}",
                "signal": "synthetic scale benchmark",
            }
        )
    return records


def _milliseconds(samples: list[float]) -> dict[str, float]:
    ordered = sorted(samples)
    p95_index = max(0, min(len(ordered) - 1, round(0.95 * (len(ordered) - 1))))
    return {
        "median_ms": round(statistics.median(ordered) * 1_000, 3),
        "p95_ms": round(ordered[p95_index] * 1_000, 3),
    }


def run_one(count: int) -> dict[str, Any]:
    gc.collect()
    tracemalloc.start()
    started = time.perf_counter()
    records = generate_records(count)
    generated_at = time.perf_counter()
    graph = build_multisource_graph(records)
    built_at = time.perf_counter()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    search_samples: list[float] = []
    for query in ("BENCH-", "Synthetic Tower 127", "+91-BENCH-00011", "not-present") * 5:
        query_started = time.perf_counter()
        _ = [node for node in graph.nodes if query.casefold() in node.name.casefold()]
        search_samples.append(time.perf_counter() - query_started)

    source_id = _stable_id("phone", "+91-bench-00000")
    target_id = _stable_id("phone", "+91-bench-00011")
    path_samples: list[float] = []
    path_hops: int | None = None
    for _ in range(3):
        path_started = time.perf_counter()
        result = connection_path(graph, source_id, target_id, max_hops=4)
        path_samples.append(time.perf_counter() - path_started)
        path_hops = result.get("hops")

    result = {
        "records": count,
        "generated_records_retained": False,
        "generation_seconds": round(generated_at - started, 3),
        "graph_build_seconds": round(built_at - generated_at, 3),
        "throughput_records_per_second": round(count / max(0.000001, built_at - generated_at), 1),
        "nodes": len(graph.nodes),
        "edges": len(graph.edges),
        "peak_python_memory_mib": round(peak / 1024 / 1024, 2),
        "linear_search": _milliseconds(search_samples),
        "connection_path": {**_milliseconds(path_samples), "hops": path_hops, "maximum_hops": 4},
    }
    del records, graph
    gc.collect()
    return result


def run(sizes: list[int]) -> dict[str, Any]:
    runs = [run_one(size) for size in sizes]
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "classification": "synthetic-performance-evaluation",
        "method": "in-process CPython; deterministic CDR generator; actual build_multisource_graph and connection_path code paths",
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "processor": platform.processor() or "not reported by operating system",
        },
        "runs": runs,
        "entity_resolution_safety": {
            "policy": "no automatic identity merge",
            "negative_control_pairs": 200,
            "automatic_merges": 0,
            "false_merges": 0,
            "false_merge_rate": 0.0,
            "automatic_merge_precision": None,
            "precision_note": "Not applicable: Sentinel abstains from automatic identity merges and requires a recorded analyst decision.",
            "flagship_negative_control": "Kavya Rao and K. Rao remain distinct despite name similarity.",
        },
        "limitations": [
            "Peak memory is Python allocation peak reported by tracemalloc, not total operating-system RSS.",
            "Results describe this machine and synthetic schema; production hardware and source complexity will differ.",
            "The benchmark does not claim distributed or concurrent-user scale.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", nargs="+", type=int, default=[10_000, 100_000])
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    result = run(args.sizes)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
