# Shock Events Schema

| Field | Type | Description |
| --- | --- | --- |
| `event_id` | string | Unique identifier for the shock (e.g., `CR-2025-04`). |
| `name` | string | Short label for the event. |
| `type` | string | Category (e.g., `continuing_resolution`, `world_event`, `policy_change`). |
| `start_tick` | integer | Simulation tick when the shock begins. |
| `duration` | integer | Number of ticks the shock lasts. |
| `budget_impact` | number | Multiplier or additive effect on `funding_rdte`/`funding_om`. |
| `affected_domains` | string | Semicolon-separated list of domains (e.g., `ISR;Cyber`). |
| `description` | string | Narrative summary for analysts. |
| `confidence` | number | [0..1] indicator of how well vetted the event is (used to gate scenario selection). |

Hook this CSV into the Mesa model by loading the table at run-time, scheduling `RdteModel._in_shock` toggles, and applying the `budget_impact` multiplier for ticks between `start_tick` and `start_tick + duration`. Events can also seed `metadata` or event logs when the `type` is `policy_change` so downstream reporting ties gate outcomes to external shocks.
