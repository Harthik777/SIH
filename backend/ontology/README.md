# Crime ontology assets

- `final_ontology.ttl` is the supplied WebProtégé schema with 13 classes, 12 object properties, and 7 datatype properties.
- `populated_crime_ontology.ttl` is the supplied populated graph generated from the 500-record crime dataset.

Runtime graph construction follows the same core mappings while producing UI-ready node and edge objects. The API endpoint `GET /api/ontology/summary` exposes the schema labels and counts used by the application.

