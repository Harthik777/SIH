"""Deterministic graph analytics derived from the currently active evidence graph."""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter, defaultdict, deque
from datetime import datetime
from typing import Any

from .models import Alert, GraphNode, GraphPayload


def adjacency(payload: GraphPayload) -> dict[str, set[str]]:
    graph = {node.id: set() for node in payload.nodes}
    for edge in payload.edges:
        if edge.source in graph and edge.target in graph:
            graph[edge.source].add(edge.target)
            graph[edge.target].add(edge.source)
    return graph


def structure_metrics(payload: GraphPayload) -> dict[str, Any]:
    graph = adjacency(payload)
    node_count = len(payload.nodes)
    edge_count = len(payload.edges)
    degrees = {node_id: len(neighbors) for node_id, neighbors in graph.items()}
    community_degree: Counter[int] = Counter()
    internal_edges = 0
    community_by_id = {node.id: node.community for node in payload.nodes}
    for node in payload.nodes:
        community_degree[node.community] += degrees[node.id]
    for edge in payload.edges:
        if community_by_id.get(edge.source) == community_by_id.get(edge.target):
            internal_edges += 1
    modularity = 0.0
    if edge_count:
        modularity = internal_edges / edge_count - sum((degree / (2 * edge_count)) ** 2 for degree in community_degree.values())

    seen: set[str] = set()
    components = 0
    for start in graph:
        if start in seen:
            continue
        components += 1
        queue = [start]
        seen.add(start)
        while queue:
            current = queue.pop()
            for neighbor in graph[current] - seen:
                seen.add(neighbor)
                queue.append(neighbor)

    possible_edges = node_count * (node_count - 1) / 2
    return {
        "nodes": node_count,
        "edges": edge_count,
        "components": components,
        "average_degree": round(2 * edge_count / node_count, 3) if node_count else 0,
        "density": round(edge_count / possible_edges, 6) if possible_edges else 0,
        "modularity": round(modularity, 4),
        "max_degree": max(degrees.values(), default=0),
        "average_risk": round(sum(node.risk for node in payload.nodes) / node_count, 1) if node_count else 0,
    }


def _sampled_betweenness(graph: dict[str, set[str]], sample_size: int = 32) -> dict[str, float]:
    """Brandes betweenness on a deterministic source sample, scaled to [0, 1]."""
    nodes = sorted(graph)
    if not nodes:
        return {}
    if len(nodes) <= sample_size:
        sources = nodes
    else:
        step = len(nodes) / sample_size
        sources = [nodes[min(len(nodes) - 1, int(index * step))] for index in range(sample_size)]
    scores = dict.fromkeys(nodes, 0.0)
    for source in sources:
        stack: list[str] = []
        predecessors: dict[str, list[str]] = {node: [] for node in nodes}
        paths = dict.fromkeys(nodes, 0.0)
        paths[source] = 1.0
        distance = dict.fromkeys(nodes, -1)
        distance[source] = 0
        queue: deque[str] = deque([source])
        while queue:
            current = queue.popleft()
            stack.append(current)
            for neighbor in graph[current]:
                if distance[neighbor] < 0:
                    queue.append(neighbor)
                    distance[neighbor] = distance[current] + 1
                if distance[neighbor] == distance[current] + 1:
                    paths[neighbor] += paths[current]
                    predecessors[neighbor].append(current)
        dependency = dict.fromkeys(nodes, 0.0)
        while stack:
            target = stack.pop()
            for predecessor in predecessors[target]:
                if paths[target]:
                    dependency[predecessor] += (paths[predecessor] / paths[target]) * (1 + dependency[target])
            if target != source:
                scores[target] += dependency[target]
    maximum = max(scores.values(), default=0.0)
    return {node: value / maximum if maximum else 0.0 for node, value in scores.items()}


def centrality(payload: GraphPayload, metric: str = "influence", limit: int = 20, entity_type: str | None = None) -> list[dict[str, Any]]:
    graph = adjacency(payload)
    nodes = {node.id: node for node in payload.nodes}
    denominator = max(1, len(nodes) - 1)
    degree = {node_id: len(neighbors) / denominator for node_id, neighbors in graph.items()}
    maximum_degree = max(map(len, graph.values()), default=1)
    degree_scaled = {node_id: len(neighbors) / maximum_degree for node_id, neighbors in graph.items()}
    between = _sampled_betweenness(graph)
    # Harmonic reach from the same deterministic source set would privilege sampled
    # sources. This local neighborhood reach is exact and stable for all nodes.
    reach = {
        node_id: min(1.0, (len(neighbors) + sum(len(graph[item]) for item in neighbors) * 0.35) / max(1, max(map(len, graph.values()), default=1) * 2))
        for node_id, neighbors in graph.items()
    }
    values = {
        node_id: {
            "degree": degree[node_id],
            "betweenness": between.get(node_id, 0.0),
            "reach": reach[node_id],
            "influence": 0.45 * degree_scaled[node_id] + 0.4 * between.get(node_id, 0.0) + 0.15 * reach[node_id],
        }
        for node_id in nodes
    }
    selected = metric if metric in {"degree", "betweenness", "reach", "influence"} else "influence"
    candidates = [node for node in nodes.values() if not entity_type or node.type == entity_type]
    ranked = sorted(candidates, key=lambda node: (-values[node.id][selected], -node.risk, node.name))[:limit]
    return [
        {
            "node": node,
            "rank": index + 1,
            "score": round(values[node.id][selected], 6),
            "metric": selected,
            "degree": len(graph[node.id]),
            "degree_centrality": round(degree[node.id], 6),
            "betweenness_approx": round(between.get(node.id, 0.0), 6),
            "neighborhood_reach": round(reach[node.id], 6),
            "method": "deterministic sampled Brandes (32 sources)" if selected in {"betweenness", "influence"} else "exact local topology",
        }
        for index, node in enumerate(ranked)
    ]


def degree_distribution(payload: GraphPayload) -> list[dict[str, int]]:
    counts = Counter(len(neighbors) for neighbors in adjacency(payload).values())
    return [{"degree": degree, "nodes": count} for degree, count in sorted(counts.items())]


def timeline(payload: GraphPayload, limit: int = 1000) -> list[dict[str, Any]]:
    graph = adjacency(payload)
    nodes = {node.id: node for node in payload.nodes}
    dated: list[tuple[datetime, GraphNode]] = []
    for node in payload.nodes:
        if node.type != "event" or not node.lastSeen:
            continue
        try:
            dated.append((datetime.fromisoformat(node.lastSeen), node))
        except ValueError:
            continue
    events = []
    for occurred_at, node in sorted(dated, key=lambda item: item[0], reverse=True)[:limit]:
        neighbors = sorted(graph[node.id], key=lambda item: (-nodes[item].risk, nodes[item].name))
        severity = "critical" if node.risk >= 85 else "high" if node.risk >= 70 else "medium" if node.risk >= 45 else "low"
        events.append(
            {
                "id": f"timeline-{node.id}",
                "date": occurred_at.strftime("%d %b"),
                "time": occurred_at.strftime("%H:%M"),
                "occurred_at": occurred_at.isoformat(),
                "title": node.name if "generic-schema" in (node.tags or []) else node.description.split(" — ", 1)[0] if node.description else node.name,
                "description": node.description or f"{node.name} linked to {len(neighbors)} resolved entities.",
                "type": "event",
                "severity": severity,
                "risk": node.risk,
                "entities": neighbors,
                "case_id": node.id,
            }
        )
    return events


def risk_trend(payload: GraphPayload) -> list[dict[str, Any]]:
    buckets: dict[str, list[GraphNode]] = defaultdict(list)
    for node in payload.nodes:
        if node.type == "event" and node.lastSeen:
            try:
                key = datetime.fromisoformat(node.lastSeen).strftime("%b")
            except ValueError:
                continue
            buckets[key].append(node)
    month_order = {datetime(2000, month, 1).strftime("%b"): month for month in range(1, 13)}
    return [
        {
            "period": period,
            "average_risk": round(sum(node.risk for node in nodes) / len(nodes), 1),
            "review_signals": sum(node.risk >= 85 for node in nodes),
            "incidents": len(nodes),
        }
        for period, nodes in sorted(buckets.items(), key=lambda item: month_order.get(item[0], 99))
    ]


def locations(payload: GraphPayload, limit: int = 30) -> list[dict[str, Any]]:
    graph = adjacency(payload)
    beat_nodes = [node for node in payload.nodes if node.type == "location" and "police-beat" in (node.tags or [])]
    location_nodes = beat_nodes or [node for node in payload.nodes if node.type == "location"]
    ranked = sorted(location_nodes, key=lambda node: (-len(graph[node.id]), -node.risk, node.name))[:limit]
    india_context = any("bengaluru" in f"{node.name} {node.location or ''}".casefold() or "karnataka" in f"{node.name} {node.location or ''}".casefold() for node in location_nodes)
    results = []
    for node in ranked:
        digest = hashlib.sha256(node.id.encode("utf-8")).digest()
        x = 28 + digest[0] / 255 * 44
        y = 14 + digest[1] / 255 * 70
        # Regional bounds support interoperable GeoJSON but remain explicitly
        # labelled display proxies, never evidentiary source coordinates.
        if india_context:
            lng = 77.42 + (x - 28) / 44 * 0.42
            lat = 13.14 - (y - 14) / 70 * 0.42
        else:
            lng = -87.94 + (x - 28) / 44 * 0.42
            lat = 42.02 - (y - 14) / 70 * 0.38
        results.append(
            {
                "id": node.id,
                "name": node.name,
                "x": round(x, 2),
                "y": round(y, 2),
                "lat": round(lat, 5),
                "lng": round(lng, 5),
                "count": len(graph[node.id]),
                "risk": node.risk,
                "entity_id": node.id,
                "coordinate_basis": "operational-grid proxy; not source GPS" if beat_nodes else "source location without coordinates; display proxy, not source GPS",
            }
        )
    return results


def generated_alerts(payload: GraphPayload, acknowledged: set[str] | None = None) -> list[Alert]:
    acknowledged = acknowledged or set()
    graph = adjacency(payload)
    nodes = {node.id: node for node in payload.nodes}

    def ranked(entity_type: str, tag: str | None = None) -> list[GraphNode]:
        values = [node for node in payload.nodes if node.type == entity_type and (not tag or tag in (node.tags or []))]
        return sorted(values, key=lambda node: (-len(graph[node.id]), -node.risk, node.name))

    people = ranked("person", "repeat-subject") or ranked("person")
    beats = ranked("location", "police-beat")
    repeat_locations = ranked("location", "repeat-location")
    vehicles = ranked("vehicle")
    high_events = sorted((node for node in payload.nodes if node.type == "event"), key=lambda node: (-node.risk, node.name))
    alerts: list[Alert] = []

    def add(alert_id: str, title: str, detail: str, severity: str, node: GraphNode, confidence: int) -> None:
        alerts.append(Alert(id=alert_id, title=title, detail=detail, severity=severity, time="active dataset", entityId=node.id, acknowledged=alert_id in acknowledged, confidence=confidence))

    if high_events:
        top = high_events[0]
        count = sum(node.risk >= 85 for node in high_events)
        add("derived-high-severity", "High-severity case cluster", f"{count} incident nodes meet the transparent ≥85 review threshold; {top.name} is the highest-ranked case.", "critical" if count else "medium", top, top.confidence)
    if people:
        top = people[0]
        add("derived-repeat-subject", "Repeat subject connectivity", f"{top.name} is linked to {len(graph[top.id])} evidence nodes. Identity must be verified in source records.", "high", top, top.confidence)
    if beats:
        top = beats[0]
        add("derived-beat-concentration", "Police-beat concentration", f"{top.name} contains {len(graph[top.id])} linked incidents, the highest active-dataset concentration.", "high", top, top.confidence)
    if repeat_locations:
        top = repeat_locations[0]
        add("derived-repeat-location", "Repeat location pattern", f"{top.name} connects {len(graph[top.id])} incidents across the active graph.", "medium", top, top.confidence)
    if vehicles:
        top = vehicles[0]
        person_links = [nodes[item].name for item in graph[top.id] if nodes[item].type == "person"]
        add("derived-vehicle-link", "Vehicle association resolved", f"{top.name} has {len(graph[top.id])} direct graph link(s)" + (f", including {person_links[0]}." if person_links else "."), "low", top, top.confidence)
    return alerts
