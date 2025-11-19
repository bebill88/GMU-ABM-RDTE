# Collaboration Network Schema

| Field | Type | Description |
| --- | --- | --- |
| `edge_id` | string | Unique ID for the relationship (e.g., `EDGE-7600A-001`). |
| `from_entity_id` | string | Entity A ID (lab, service, agency, vendor). |
| `to_entity_id` | string | Entity B ID. |
| `from_entity_type` | string | One of `Service`, `Agency`, `COCOM`, `FFRDC`, `Lab`, `Vendor`. |
| `to_entity_type` | string | Same set as above. |
| `instrument_type` | string | Collaboration instrument (`7600A`, `7600B`, `MOU`, `CRADA`, `OTA`, etc.). |
| `domain` | string | Capability domain (ISR, EW, AI, Cyber, etc.). |
| `start_year` | integer | Year when the agreement began. |
| `end_year` | integer | Year it ended (use `9999` for ongoing). |
| `intensity` | number | 0–1 or 1–5 measure of collaboration strength/commitment. |
| `note` | string | Optional human context for reporting audiences. |

Use this relationship graph to compute `network_centrality_score` and ecosystem bonuses: build an adjacency list from the `from`/`to` pairs, weight each node by `intensity`, and aggregate per `program_id` via the linked labs/agencies/vendors. These scores can then influence `innovation_leverage_factor`, `ecosystem_support`, or `service_component` alignment in `ResearcherAgent`. Keep the CSV next to `data/stubs/collaboration_network.csv` until you replace it with real exports, and validate it with the documented fields before ingesting.
