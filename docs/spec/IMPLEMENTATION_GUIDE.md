# Implementation Guide - Knowledge Graph Investigation Platform

## How to Use These Prompts with Codex

### Option 1: Use the Quick Prompt (Fastest)
Copy the entire contents of `codex_quick_prompt.txt` and paste directly into Codex in a single message. This is the most concise and action-oriented version.

### Option 2: Use the Detailed Prompt (Most Complete)
Share `codex_website_prompt.md` with Codex for more context and detailed requirements. Better if you want to iterate on specific components.

### Option 3: Chunked Approach (Best for Complex Builds)
Break it into phases and give Codex multiple prompts:
1. **Phase 1**: "Build the React frontend dashboard structure with the 12 main components (upload, graph, timeline, map, risk, explanation, alerts, analytics, search, profile, export, settings)"
2. **Phase 2**: "Build the FastAPI backend with all required endpoints"
3. **Phase 3**: "Integrate Neo4j knowledge graph and PostgreSQL"
4. **Phase 4**: "Implement the NLP pipeline processing"
5. **Phase 5**: "Add WebSocket real-time updates and animations"

## File Structure You Should Provide to Codex

When you give Codex the prompt, reference or attach these files:

```
project-root/
├── ontology/
│   └── schema.ttl          (Your ontology definitions)
├── models/
│   ├── entity_extractor.py (Pre-trained entity extraction model)
│   ├── relation_extractor.py (Relation extraction model)
│   └── risk_scorer.py      (Risk scoring logic)
├── config/
│   ├── models.yaml         (Model configurations)
│   ├── pipeline.yaml       (Pipeline parameters)
│   └── entities.yaml       (Entity type definitions)
├── data/
│   └── sample.csv          (Sample input data for testing)
└── requirements.txt        (Python dependencies)
```

## Key Files to Share with Codex

Tell Codex: *"Here are supporting files to integrate:"*

1. **Ontology (TTL)**: 
   - Share your `schema.ttl` or RDF ontology
   - Tell Codex to use it to define entity types and relationships
   - Example: `"Load entity types from ontology: Person, Organization, Location, Event, etc."`

2. **Python Models**:
   - Share your entity/relation extraction Python files
   - Tell Codex: `"Integrate the provided entity_extractor.py and relation_extractor.py into the pipeline"`
   - Specify model versions (e.g., spaCy en_core_web_md)

3. **Configuration Files**:
   - Share any existing YAML/JSON config files
   - Codex can use these to set default parameters

4. **Sample Data**:
   - Provide a sample CSV/JSON with expected format
   - Helps Codex generate appropriate data parsing logic

## Implementation Priorities (Suggest to Codex)

**Priority 1 (MVP - Week 1)**:
- Data upload with file parsing
- Basic graph visualization (nodes, edges)
- NLP pipeline (entity + relation extraction)
- Neo4j graph storage
- Simple API endpoints (upload, get nodes, get edges)

**Priority 2 (Core Analytics - Week 2)**:
- Graph analytics (centrality, clustering)
- Risk scoring algorithm
- Timeline view
- Location map
- Search and filter functionality

**Priority 3 (AI Features - Week 3)**:
- Anomaly detection
- Link prediction
- Explanation engine
- Alerts system
- Advanced visualizations (embeddings, community detection)

**Priority 4 (Polish - Week 4)**:
- Report generation (PDF)
- Dark mode
- Settings panel
- User authentication
- Performance optimization
- Docker deployment

## Technical Decisions to Mention to Codex

### Frontend Visualization Library
Tell Codex: *"For graph visualization, use Cytoscape.js (for performance) or Vis.js (for simplicity). D3.js for distribution charts and analytics visualizations."*

### Database Schema
Codex should create:

```
PostgreSQL Tables:
- users (id, email, role)
- uploads (id, filename, upload_date, user_id, status)
- processing_logs (id, upload_id, stage, message, timestamp)
- investigations (id, name, graph_data_version, created_date)
- alerts (id, investigation_id, anomaly_type, risk_score, timestamp)
- saved_filters (id, user_id, filter_json, created_date)

Neo4j Nodes:
- Entity nodes (type: Person, Organization, Location, Event, etc.)
  properties: name, type, confidence, risk_score, metadata

Neo4j Relationships:
- RELATES_TO (with relationship_type property)
- LOCATED_AT
- WORKS_FOR
- OWNS
- CREATED
- etc. (based on your ontology)
```

### API Authentication
Suggest to Codex: *"Use JWT tokens for API authentication. Frontend stores token in secure httpOnly cookie. Include Bearer token in Authorization headers for all protected endpoints."*

### Real-time Updates
Tell Codex: *"Use WebSocket (socket.io or raw ws) to stream pipeline progress updates. When graph is modified, emit graph_updated events to all connected clients."*

## Specific Prompts for Each Component

### For NLP Pipeline
```
"Create a Python service that:
1. Takes raw data (CSV/JSON)
2. Loads the ontology from schema.ttl
3. Runs entity extraction using spaCy + HuggingFace transformers
4. Runs relation extraction to find connections
5. Stores entities and relations in Neo4j
6. Returns progress updates via WebSocket
Integrate with the provided entity_extractor.py and relation_extractor.py models."
```

### For Graph Visualization
```
"Create an interactive network graph visualization using Cytoscape.js that:
1. Displays nodes (entities) colored by type
2. Shows edge labels (relationship types)
3. Supports zoom, pan, search, filter
4. Allows clicking nodes to show detailed profile panel
5. Supports multiple layout algorithms
6. Highlights communities with different colors
7. Shows node size proportional to centrality score
8. Real-time updates when graph changes via WebSocket"
```

### For Anomaly Detection
```
"Implement anomaly detection that:
1. Analyzes the knowledge graph structure
2. Flags unusual connection patterns (e.g., dense clusters, bridge nodes)
3. Detects statistical outliers in entity properties
4. Predicts hidden links between entities
5. Scores each entity for risk (0-100)
6. Provides natural language explanation for each anomaly
7. Uses Isolation Forest for statistical anomalies
8. Uses graph-based methods for structural anomalies"
```

### For Explanation Engine
```
"Create an explanation engine that:
1. For each flagged anomaly or risk score, generates human-readable explanation
2. Shows supporting evidence (related nodes, patterns)
3. Displays confidence level
4. Uses LIME or rule-based approach to explain ML predictions
5. Provides 'Explain More' option with technical details
6. Highlights relevant subgraph that caused the flag
7. Suggests alternative hypotheses"
```

## Quality Checklist for Codex

After Codex builds the system, verify:

- [ ] Can upload CSV/JSON/TTL files
- [ ] Pipeline processes data and shows real-time progress
- [ ] Entities and relations appear in Neo4j
- [ ] Graph visualization renders smoothly with 1000+ nodes
- [ ] All 12 dashboard components load and function
- [ ] Filters apply correctly and instantly
- [ ] Search with autocomplete works
- [ ] Risk scores calculated and displayed
- [ ] Anomalies detected and flagged
- [ ] Timeline syncs with graph view
- [ ] Map shows geospatial data
- [ ] Explanations are generated for findings
- [ ] Alerts trigger for high-risk items
- [ ] Export to PDF/CSV/JSON works
- [ ] WebSockets deliver real-time updates
- [ ] Dark mode toggles properly
- [ ] Mobile responsive (test on tablet size)
- [ ] Performance: <1s response for searches/filters
- [ ] Can handle 10K+ node graphs without crashes

## Common Issues Codex Might Overlook (Remind Them)

1. **Graph Performance**: Cytoscape may slow down with 10K+ nodes. Suggest pagination, clustering, or viewport-based rendering.

2. **Database Indexing**: Neo4j needs proper indexes on frequently queried properties (name, type, risk_score).

3. **Memory Usage**: Large graph processing needs streaming/batching. Don't load entire graph into memory at once.

4. **CORS**: If frontend and backend on different ports, remember to enable CORS in FastAPI.

5. **Model Loading**: Large NLP models take time to load. Codex should load once at startup, not per request.

6. **Real-time Sync**: WebSocket connections need proper cleanup on disconnect to prevent memory leaks.

7. **Error Handling**: Need proper try-catch and error logging for pipeline failures.

8. **Security**: Sanitize all user inputs, validate file uploads, implement rate limiting on APIs.

## If Codex Gets Stuck

Try these follow-up prompts:

- *"The graph is too slow with 10K nodes. Implement viewport-based rendering or clustering."*
- *"Add caching for expensive graph computations using Redis."*
- *"The explanation generation is taking too long. Use a simpler rule-based approach instead of LIME."*
- *"WebSocket updates aren't reaching the frontend. Debug and fix the socket.io connection."*
- *"Make the PDF export include all visualizations and findings."*

## File References to Include

When prompting Codex, reference your files like this:

> **"Here's our ontology defining entity types (see schema.ttl). Here's our entity extraction model (entity_extractor.py). Here's a sample data file showing expected input format (sample.csv). Use these as reference implementations."**

This gives Codex concrete anchors instead of abstract requirements.

## Next Steps

1. Copy `codex_quick_prompt.txt` → Paste into Codex
2. Attach/reference your ontology.ttl, Python models, and config files
3. Clarify any specific business logic (risk scoring formula, anomaly types)
4. Request incremental delivery (MVP first, then features)
5. Ask for Docker setup and API documentation
6. Have Codex generate test data for demo purposes
