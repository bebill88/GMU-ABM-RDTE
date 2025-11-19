# GAO Findings Schema

| Field | Type | Description |
| --- | --- | --- |
| `finding_id` | string | Unique GAO action item identifier (e.g., GAO-25-123). |
| `program_id` | string | PE/program identifier to link the finding to an ABM researcher. |
| `year` | integer | Fiscal year of the GAO action. |
| `issue_area` | string | High-level area (e.g., "V&V", "Acquisition", "Budget Control"). |
| `severity` | string | Ordinal string (e.g., "Low", "Medium", "High") used for penalty weighting. |
| `description` | string | Short narrative for analysts and dashboards. |
| `repeat_offender` | boolean | `true` if GAO labeled the program as a recurring issue. |
| `timestamp` | string (ISO 8601) | Date when the finding was published/verified. |

The GAO findings feed into V&V and repeat-offender penalty adjustments by augmenting the `penalties` configuration or PSV scoreboard. Link each `program_id` to `RdteModel.program_index` and use `repeat_offender` plus `severity` to bump `PenaltyBook.counts` before a run. Export this schema to `data/stubs/gao_findings.csv` so teams can seed the penalty logic with realistic oversight history.
