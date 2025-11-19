# Additional Organization Data Schema

These CSVs describe the people/orgs behind each RDT&E program so you can connect the GAO, vendor, shock, and collaboration inputs to the actors that “do the work.”

1. **RDT&E Organizations / Units (`data/orgs.csv`)**

| Column | Type | Description |
| --- | --- | --- |
| `entity_id` | string | Unique ID for the organization/unit (e.g., `AFRL-RQ`). Matches `program_vendor_evaluations.vendor_id` or `collaboration_network` nodes. |
| `name` | string | Human-readable organization name. |
| `entity_type` | string | `Service`, `CCMD`, `Agency`, `Lab`, `FFRDC`, `Vendor`, etc. |
| `service_component` | string | Associated service (Army, Navy, Air Force, Space, Joint, IC). |
| `org_role` | string | Primary role (prime, integrator, test lead, sponsor). |
| `authority` | string | Title 10/Title 50/Other statutory alignment. |
| `funding_source` | string | Primary appropriation (MIP, NIP, Title 10, Other). |
| `notes` | string | Context (e.g., 7600 instrument, joint test lab, OTA lead). |

# Link CSV – Program ↔ Organization roles (`data/program_entity_roles.csv`):

| Column | Type | Description |
| --- | --- | --- |
| `program_id` | string | Matches `program_id` from the RDT&E CSV. |
| `entity_id` | string | Organization entity participating in the program. |
| `role` | string | Role (`sponsor`, `executing`, `requirements`, `test`, `ops`, `transition_partner`). |
| `effort_share` | number | 0–1 estimate of the entity’s contribution to this program. |
| `note` | string | Human-readable explanation of why the org is linked. |

This many-to-many table keeps each program connected to the `entity_id`s defined in `data/rdte_entities.csv` so GAO findings, vendor scores, shocks, and collaboration info all land on the right organizations. Use `effort_share` to weight penalties/bonuses (e.g., a sponsor with high share attracts GAO scrutiny) and `role` to decide which gate logic (test vs. funding) the org influences.

- **Program ↔ Organization Link Table (`data/program_org_links.csv`)**
  - (Retained for backwards compatibility if needed; now you can replace it with `program_entity_roles.csv`.)

| Column | Type | Description |
| --- | --- | --- |
| `link_id` | string | Unique ID for the relationship. |
| `program_id` | string | Matches `data/rdte_fy26.csv` `program_id`. |
| `entity_id` | string | Organization participating in the program. |
| `role` | string | Role in the program (`primary`, `partner`, `lab_support`, `contractor`). |
| `start_year` | integer | Year the relationship began. |
| `end_year` | integer | Year it ended or `9999` for ongoing. |
| `importance` | number | 0–1 relative weight of the org’s contribution. |
| `notes` | string | Optional detail (e.g., includes FMS, foreign partner, or MOU). |

Integration idea: use these tables along with `docs/schema_collaboration_network.md` and `docs/schema_vendor_evaluations.md` to compute penalties, bonuses, or dependency pairings (e.g., GAO findings referencing the primary lab, shocks targeted at certain org roles, vendor evaluations mapped into the link table). You can also treat `entity_id` as part of `ResearcherAgent.entity_id` and use the `importance` weights when aggregating ecosystem scores.
