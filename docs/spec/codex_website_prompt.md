# Knowledge Graph Investigation Platform - Website Build Prompt

## Project Overview
Build a full-stack web application for an AI-powered knowledge graph investigation system that processes raw data through an NLP/ML pipeline and presents findings through an interactive investigator dashboard.

## System Architecture

### Data Processing Pipeline
1. **Raw Data Input** → CSV/JSON/Database uploads
2. **Data Cleaning & Processing** → Validation, normalization, deduplication
3. **NLP Entity Extraction** → Extract entities (people, organizations, locations, events) using spaCy/transformers
4. **Relation Extraction** → Identify relationships between entities
5. **Knowledge Graph Construction** → Build knowledge graph (nodes = entities, edges = relationships)
6. **Graph Algorithms** → Apply Node2Vec embeddings, GraphSAGE, and standard graph analytics
7. **AI Analysis Engine** → Run anomaly detection, risk scoring, link prediction, community detection
8. **Dashboard Visualization** → Present results through interactive dashboard

## Frontend Architecture

### Technology Stack
- **Framework**: React 18+ with TypeScript
- **Visualization**: Vis.js or Cytoscape.js for network graphs, D3.js for advanced analytics
- **Styling**: Tailwind CSS with custom design system
- **State Management**: Redux or Zustand
- **Maps**: Leaflet.js for geolocation visualization
- **Real-time Updates**: WebSockets for live processing updates

### Core Dashboard Components

#### 1. Navigation & Layout
- Top navigation bar with logo, user profile, search bar
- Left sidebar with main sections:
  - Dashboard
  - Upload & Process Data
  - Knowledge Graph Explorer
  - Analytics
  - Settings
- Mobile-responsive hamburger menu

#### 2. Data Upload & Processing Module
- Drag-and-drop file upload (CSV, JSON, XML, RDF/TTL)
- Data preview with table display
- Processing pipeline progress indicator showing:
  - Data Cleaning status
  - Entity Extraction progress (%)
  - Relation Extraction progress (%)
  - Knowledge Graph construction status
  - Real-time console logs
- Option to configure NLP models and extraction parameters
- Upload history with timestamps

#### 3. Network Visualization (Main Dashboard)
- **Interactive Graph Display**:
  - Nodes represent entities (color-coded by type: Person, Organization, Location, Event)
  - Edges represent relationships (labeled with relation type)
  - Node size proportional to importance/centrality score
  - Zoom, pan, and search functionality
  - Hover tooltips showing entity details
  
- **Graph Controls**:
  - Filter by entity type
  - Filter by relationship type
  - Adjust algorithm (Node2Vec, GraphSAGE, standard analytics)
  - Layout options (Force-Directed, Hierarchical, Circular)
  - Clustering visualization toggle
  
- **Community Detection Visualization**:
  - Highlight detected communities with different colors
  - Show community statistics (size, density, modularity)
  - Community comparison view

#### 4. Timeline View
- Chronological visualization of events/relationships
- Interactive timeline with draggable handles
- Filter by entity or relationship type
- Hover to show event details
- Click to highlight related nodes in graph view

#### 5. Location Map
- Geospatial visualization of location-based entities
- Heat map showing activity/density
- Cluster markers for grouped entities
- Filter by entity type or time range
- Click markers to view entity details

#### 6. Risk & Anomaly Scoring Dashboard
- **Risk Score Cards**:
  - Overall risk level (0-100) with color gradient
  - Top 10 highest-risk entities displayed
  - Risk factors breakdown (suspicious patterns, outliers, anomalies)
  
- **Anomaly Detection Results**:
  - List of detected anomalies with severity levels
  - Anomaly type (unusual connections, statistical outliers, behavioral anomalies)
  - Confidence score for each anomaly
  - Graph highlighting showing anomalous subgraph

- **Link Prediction**:
  - Predicted future connections between entities
  - Probability scores for predicted links
  - Confidence intervals
  - Actionable insights

#### 7. Alerts & Notifications Panel
- Real-time alerts for high-risk anomalies
- Alert history with filtering options
- Alert details with supporting evidence
- Export alerts to PDF/CSV
- Alert acknowledgment and follow-up logging

#### 8. AI Explanation Engine Panel
- **For Each Insight**:
  - Natural language explanation of why an anomaly/risk was flagged
  - Supporting evidence (related nodes, patterns, statistical justification)
  - Confidence level
  - "Explain More" option for detailed technical breakdown
  
- **Explanation Features**:
  - Highlight relevant subgraph
  - Show calculation methodology
  - Provide alternative hypotheses
  - Reference source data

#### 9. Entity Details Panel
- Click any node to open entity profile
- Display attributes:
  - Name, type, confidence score
  - All relationships (incoming and outgoing)
  - Associated metadata
  - Risk score and anomaly flags
  - Timeline of activities
  - Location history (if applicable)
  
- **Actions**:
  - Add notes/tags
  - Flag for investigation
  - Export entity profile
  - Link to external sources
  - Create sub-investigation

#### 10. Advanced Analytics Section
- **Graph Metrics Dashboard**:
  - Number of nodes, edges, components
  - Average degree, diameter, density
  - Betweenness/closeness centrality rankings
  - Clustering coefficient
  
- **Distribution Visualizations**:
  - Degree distribution (log-log plot)
  - Entity type distribution (pie/bar chart)
  - Relationship type distribution
  - Risk score distribution
  
- **Predictive Analytics**:
  - Node2Vec embedding visualization (t-SNE/UMAP)
  - GraphSAGE generated node embeddings
  - Similarity matrix heatmap
  - Link probability predictions

#### 11. Search & Filter Interface
- Global search bar with autocomplete
- Filter options:
  - Entity type multi-select
  - Relationship type multi-select
  - Date range picker
  - Risk score range slider
  - Anomaly severity threshold
  - Confidence score threshold

- **Saved Searches/Investigations**:
  - Save filter combinations
  - Export filtered subgraph
  - Share investigation link
  - Version history

#### 12. Export & Reporting
- Export options:
  - Graph data (JSON, GraphML)
  - Subgraph selection export
  - Investigation report (PDF with visualizations)
  - Risk assessment spreadsheet
  - Timeline export (CSV)
  - Geospatial data (GeoJSON)
  
- **Report Generation**:
  - Auto-generated investigation summary
  - Include key findings, top risks, anomalies
  - Supporting visualizations
  - Executive summary

### Settings & Configuration
- **User Preferences**:
  - Theme (light/dark mode)
  - Default visualization type
  - Alert sensitivity settings
  - Notification preferences
  
- **Data & Model Settings**:
  - NLP model selection (e.g., BERT, RoBERTa)
  - Graph algorithm parameters
  - Anomaly detection thresholds
  - API configuration (if using external models)

- **Access Control**:
  - User roles (Admin, Analyst, Viewer)
  - Team management
  - Investigation permissions

## Backend Architecture

### Technology Stack
- **API Framework**: FastAPI or Flask with Python
- **Database**: PostgreSQL for metadata + Neo4j for knowledge graph
- **Task Queue**: Celery + Redis for async pipeline jobs
- **Model Serving**: FastAPI endpoints or Flask routes
- **WebSockets**: For real-time updates to frontend

### Backend Components

#### 1. Data Upload & Storage Service
- Handle multiple file formats
- Store raw data in PostgreSQL
- Validate and normalize data
- Manage upload history

#### 2. Data Pipeline Service
- Orchestrate cleaning → extraction → relation extraction
- Expose endpoints for each pipeline stage
- Stream progress updates via WebSockets
- Handle errors and retries
- Support batch and real-time processing

#### 3. NLP Engine Service
- Entity extraction using trained models
- Relation extraction using pattern matching or ML models
- Store extracted entities in graph database
- Version control for model updates
- Support custom entity/relation types

#### 4. Knowledge Graph Service
- Build and manage Neo4j graph
- CRUD operations on nodes and edges
- Graph query interface (Cypher)
- Indexing for fast queries
- Full-text search capabilities

#### 5. Graph Analytics Service
- Implement graph algorithms (centrality, clustering, community detection)
- Node2Vec embedding generation
- GraphSAGE model integration
- Generate analytics metrics
- Cache results for performance

#### 6. AI Analysis Service
- Anomaly detection algorithms
- Risk scoring logic
- Link prediction models
- Community detection
- Explanation generation (using LIME/SHAP or rule-based)

#### 7. API Endpoints

**Data Management**:
- `POST /api/upload` - Upload data file
- `GET /api/uploads` - List upload history
- `GET /api/upload/{id}` - Get upload details
- `DELETE /api/upload/{id}` - Delete upload

**Pipeline**:
- `POST /api/pipeline/start` - Start processing pipeline
- `GET /api/pipeline/status/{id}` - Get pipeline status
- `WS /api/pipeline/stream/{id}` - WebSocket for progress updates
- `GET /api/pipeline/logs/{id}` - Get processing logs

**Knowledge Graph**:
- `GET /api/graph/nodes` - Get all nodes (with pagination/filtering)
- `GET /api/graph/node/{id}` - Get node details
- `GET /api/graph/edges` - Get all edges
- `GET /api/graph/subgraph` - Get subgraph based on filters
- `POST /api/graph/search` - Search nodes/relationships
- `GET /api/graph/metrics` - Get graph statistics

**Analytics**:
- `GET /api/analytics/centrality` - Node centrality scores
- `GET /api/analytics/community` - Community detection results
- `GET /api/analytics/embeddings` - Node embeddings (Node2Vec/GraphSAGE)
- `GET /api/analytics/distribution` - Distribution statistics

**AI Analysis**:
- `GET /api/analysis/anomalies` - Detected anomalies
- `GET /api/analysis/risk-scores` - Entity risk scores
- `GET /api/analysis/link-predictions` - Predicted links
- `GET /api/analysis/explanations/{id}` - Explanation for specific finding
- `GET /api/analysis/summary` - Overall investigation summary

**Visualization**:
- `GET /api/visualization/graph` - Graph data for frontend
- `GET /api/visualization/timeline` - Timeline data
- `GET /api/visualization/locations` - Geospatial data
- `GET /api/visualization/heatmap` - Activity heatmap

**Export**:
- `GET /api/export/graph/{format}` - Export graph (JSON, GraphML, etc.)
- `GET /api/export/report/pdf` - Generate PDF report
- `GET /api/export/data/csv` - Export data as CSV
- `GET /api/export/geojson` - Export geospatial data

**Settings**:
- `GET /api/config` - Get system configuration
- `POST /api/config` - Update configuration
- `GET /api/models` - List available models
- `POST /api/models/upload` - Upload custom model

## Integration Points

### Input Files
- **Ontology**: Load RDF/TTL ontology file to define entity types, relationships, properties
- **Python Models**: Import pre-trained extraction/classification models
- **Configuration**: Load pipeline parameters from JSON/YAML config files
- **Custom Data**: Support CSV, JSON, XML, RDF inputs

### AI Models to Integrate
- NLP Entity Extraction: spaCy, HuggingFace Transformers
- Relation Extraction: Pattern-based or transformer-based models
- Graph Embeddings: Node2Vec, GraphSAGE
- Anomaly Detection: Isolation Forest, LOF, Graph-based methods
- Risk Scoring: Custom ML model or rule-based logic
- Link Prediction: Graph neural networks or similarity-based
- Community Detection: Louvain algorithm, Leiden algorithm

## Key Features Summary

✅ Multi-format data ingestion with real-time processing
✅ End-to-end NLP pipeline with extraction and relation identification
✅ Interactive knowledge graph visualization
✅ Advanced analytics (centrality, embeddings, community detection)
✅ AI-powered anomaly detection and risk scoring
✅ Link prediction for hidden connections
✅ Timeline and geospatial visualizations
✅ Comprehensive alerts and explanation engine
✅ Export in multiple formats
✅ Role-based access control
✅ Responsive, modern UI
✅ Real-time WebSocket updates
✅ Scalable architecture for large graphs

## Deployment Considerations
- Containerize with Docker
- Use docker-compose for local development
- Support cloud deployment (AWS/GCP/Azure)
- Implement caching for performance (Redis)
- Database backups and versioning
- Monitoring and logging (ELK stack)
- API rate limiting and security (JWT auth)

## Performance Requirements
- Handle graphs with 10K+ nodes
- Sub-second search/filter response times
- Real-time graph updates via WebSockets
- Efficient memory usage for large datasets
- Parallel processing of pipeline stages

## Accessibility & User Experience
- WCAG 2.1 AA compliance
- Keyboard navigation support
- Intuitive tooltip help system
- Error messages with solutions
- Dark mode for eye comfort
- Export data for offline analysis
- Undo/redo functionality where applicable
