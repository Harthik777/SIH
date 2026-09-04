import hashlib

from .models import Alert, GraphEdge, GraphNode


def _id(prefix: str, value: str) -> str:
    return f"{prefix}_{hashlib.sha1(value.encode('utf-8'), usedforsecurity=False).hexdigest()[:12]}"


NODES = [
    GraphNode(id="n1", name="Marcus Chen", type="person", risk=92, confidence=96, community=1, aliases=["M. Chen", "MC-7"], description="Primary subject connected to three high-risk financial clusters.", location="Singapore", lastSeen="Today, 09:42", tags=["priority", "financial"]),
    GraphNode(id="n2", name="Nexus Holdings", type="organization", risk=88, confidence=94, community=1, description="Offshore holding company registered in 2019.", location="British Virgin Islands", lastSeen="Aug 28, 2026", tags=["offshore"]),
    GraphNode(id="n3", name="Elena Vasquez", type="person", risk=73, confidence=89, community=1, location="Madrid, ES", lastSeen="Sep 2, 2026"),
    GraphNode(id="n4", name="Aurum Trust", type="organization", risk=81, confidence=91, community=2, description="Private trust appearing in 14 transaction records.", location="Zurich, CH", lastSeen="Aug 31, 2026"),
    GraphNode(id="n5", name="Port Meridian", type="location", risk=45, confidence=98, community=3, location="Singapore", lastSeen="Sep 1, 2026"),
    GraphNode(id="n6", name="AC-8841", type="account", risk=97, confidence=99, community=1, description="Account with abnormal circular transfer pattern.", location="Cayman Islands", lastSeen="Today, 09:42", tags=["frozen", "priority"]),
    GraphNode(id="n7", name="Northstar Logistics", type="organization", risk=64, confidence=87, community=3, location="Rotterdam, NL", lastSeen="Aug 29, 2026"),
    GraphNode(id="n8", name="Lena Okafor", type="person", risk=38, confidence=84, community=2, location="Lagos, NG", lastSeen="Aug 26, 2026"),
    GraphNode(id="n9", name="Project Halcyon", type="event", risk=77, confidence=82, community=2, description="Coordinated series of cross-border transfers.", location="Multiple", lastSeen="Aug 30, 2026"),
    GraphNode(id="n10", name="Vega Exports", type="organization", risk=56, confidence=93, community=3, location="Panama City, PA", lastSeen="Aug 24, 2026"),
    GraphNode(id="n11", name="Sofia Marin", type="person", risk=61, confidence=88, community=2, location="Lisbon, PT", lastSeen="Aug 31, 2026"),
    GraphNode(id="n12", name="AC-2109", type="account", risk=84, confidence=97, community=2, location="Luxembourg", lastSeen="Sep 2, 2026"),
    GraphNode(id="n13", name="Atlas Freeport", type="location", risk=69, confidence=90, community=3, location="Geneva, CH", lastSeen="Aug 25, 2026"),
    GraphNode(id="n14", name="Ilya Petrov", type="person", risk=52, confidence=79, community=3, location="Tallinn, EE", lastSeen="Aug 22, 2026"),
]

EDGES = [
    GraphEdge(id="e1", source="n1", target="n2", label="CONTROLS", confidence=94, anomalous=True),
    GraphEdge(id="e2", source="n1", target="n6", label="BENEFICIARY", confidence=98, anomalous=True),
    GraphEdge(id="e3", source="n2", target="n6", label="OWNS", confidence=96),
    GraphEdge(id="e4", source="n3", target="n2", label="DIRECTOR_OF", confidence=89),
    GraphEdge(id="e5", source="n4", target="n12", label="OWNS", confidence=93),
    GraphEdge(id="e6", source="n8", target="n4", label="TRUSTEE_OF", confidence=84),
    GraphEdge(id="e7", source="n11", target="n4", label="ADVISOR_TO", confidence=81),
    GraphEdge(id="e8", source="n12", target="n9", label="FUNDED", confidence=88, anomalous=True),
    GraphEdge(id="e9", source="n6", target="n12", label="TRANSFERRED_TO", confidence=99, anomalous=True),
    GraphEdge(id="e10", source="n9", target="n1", label="ASSOCIATED_WITH", confidence=76),
    GraphEdge(id="e11", source="n7", target="n5", label="OPERATES_AT", confidence=95),
    GraphEdge(id="e12", source="n10", target="n7", label="SHIPPED_VIA", confidence=86),
    GraphEdge(id="e13", source="n10", target="n13", label="STORED_AT", confidence=82),
    GraphEdge(id="e14", source="n14", target="n7", label="DIRECTOR_OF", confidence=78),
    GraphEdge(id="e15", source="n2", target="n7", label="CONTRACTED", confidence=72),
    GraphEdge(id="e16", source="n13", target="n4", label="LINKED_TO", confidence=68),
    GraphEdge(id="e17", source="n3", target="n11", label="ASSOCIATE", confidence=74),
]

ALERTS = [
    Alert(id="a1", title="Armed robbery pattern", detail="Armed-handgun robbery incidents form a high-severity cluster across multiple police beats.", severity="critical", time="4 min ago", entityId=_id("crime", "ROBBERY"), confidence=97),
    Alert(id="a2", title="Repeat subject detected", detail="Tyler Wilson appears in three separate FIR records with shared offense characteristics.", severity="high", time="18 min ago", entityId=_id("suspect", "Tyler Wilson"), confidence=91),
    Alert(id="a3", title="Police beat threshold exceeded", detail="Beat 2012 contains 35 incidents, above the dataset-wide beat baseline.", severity="high", time="1 hr ago", entityId=_id("beat", "2012"), confidence=88),
    Alert(id="a4", title="Repeat location identified", detail="1500XX W 55TH ST appears in three incident records across different dates.", severity="medium", time="3 hrs ago", entityId=_id("location", "1500XX W 55TH ST"), acknowledged=True, confidence=79),
    Alert(id="a5", title="Vehicle association resolved", detail="Plate IL-4258-DT is connected to a named suspect through narrative evidence.", severity="low", time="Yesterday", entityId=_id("vehicle", "IL-4258-DT"), acknowledged=True, confidence=92),
]

TIMELINE = [
    {"id": "t1", "date": "22 Jul", "time": "20:23", "title": "Criminal damage reported", "description": "Case JC100452 linked to a residence in Police Beat 0412.", "type": "event", "severity": "high", "entities": [_id("case", "JC100452"), _id("beat", "0412")]},
    {"id": "t2", "date": "04 Jun", "time": "09:27", "title": "Vehicle-linked armed robbery", "description": "Deandre Allen and plate IL-4258-DT extracted from FIR JC100113.", "type": "person", "severity": "critical", "entities": [_id("suspect", "Deandre Allen"), _id("vehicle", "IL-4258-DT")]},
    {"id": "t3", "date": "05 Mar", "time": "21:30", "title": "Armed robbery at alley", "description": "Case JC100339 connected to Devon Wright and the robbery cluster.", "type": "event", "severity": "critical", "entities": [_id("case", "JC100339"), _id("crime", "ROBBERY")]},
    {"id": "t4", "date": "20 Jan", "time": "10:31", "title": "Theft case ingested", "description": "Tyler Wilson and a linked vehicle resolved from narrative evidence.", "type": "event", "severity": "medium", "entities": [_id("case", "JC100226"), _id("suspect", "Tyler Wilson")]},
]

LOCATIONS = [
    {"id": "beat2012", "name": "Police Beat 2012", "lat": 41.9535, "lng": -87.7193, "count": 35, "risk": 88},
    {"id": "beat0914", "name": "Police Beat 0914", "lat": 41.8089, "lng": -87.6742, "count": 32, "risk": 83},
    {"id": "beat1622", "name": "Police Beat 1622", "lat": 41.9742, "lng": -87.8071, "count": 31, "risk": 72},
    {"id": "beat0313", "name": "Police Beat 0313", "lat": 41.7801, "lng": -87.6033, "count": 30, "risk": 81},
    {"id": "beat2411", "name": "Police Beat 2411", "lat": 42.0054, "lng": -87.6722, "count": 30, "risk": 67},
    {"id": "beat1013", "name": "Police Beat 1013", "lat": 41.8554, "lng": -87.7198, "count": 29, "risk": 75},
]
