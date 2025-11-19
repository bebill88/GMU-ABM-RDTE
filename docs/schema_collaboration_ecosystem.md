# Collaboration Ecosystem Schema

| Field | Type | Description |
| --- | --- | --- |
| `entity_id` | string | Unique identifier for the lab/hub/MOU entry. |
| `name` | string | Facility, lab, or MOU partner name. |
| `entity_type` | string | `lab`, `hub`, `MOU`, `task_force`, etc. |
| `location` | string | City/state or geocode. |
| `services_involved` | string | Semicolon-separated service components (Army;Navy;AF). |
| `mou_status` | string | `active`, `pending`, `expired`. |
| `funding_source` | string | Funding stream or sponsor. |
| `funding_amount` | number | Dollars committed through the collaboration (USD). |
| `focus_area` | string | Capability focus (e.g., `CBRNE`, `Data`, `TS/SS`). |
| `notes` | string | Context for the collaboration (7600s, extension, glove programs, etc.). |

Load this CSV into `RdteModel._load_labs` or a similar helper to supplement regional/lab attributes. Collaboration entries can seed `researcher.portfolio`, feed `ecosystem_support` bonuses, and cue network metrics (e.g., the `network_centrality_score` that you already derive for RDT&E rows). Track `entity_type` to pivot between labs vs. agreements and highlight the `funding_amount` when calculating `Innovation_Leverage_Factor`.
