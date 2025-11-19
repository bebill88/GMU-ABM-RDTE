# GAO Findings Schema

| Field | Type | Description |
| --- | --- | --- |
| `finding_id` | string | Unique GAO finding identifier (e.g., `GAO22-105123-F1`). |
| `report_id` | string | GAO report number (`GAO-22-105123`). |
| `report_year` | integer | Fiscal/calendar year of the report. |
| `program_id` | string | Internal ID matching the RDT&E program row. |
| `program_name` | string | Human-readable program title (optional redundancy). |
| `authority` | string | Statutory authority (Title 10, Title 50, etc.). |
| `funding_source` | string | MIP/NIP/Title 10 categorization from the GAO narrative. |
| `domain` | string | Capability domain (ISR, EW, Cyber, Space, etc.). |
| `org_type` | string | Operator type (Service, COCOM, Agency, FFRDC, etc.). |
| `finding_type` | string | Enum: `cost`, `schedule`, `performance`, `governance`, `compliance`, `security`. |
| `severity` | integer | 1–5 ordinal (1=minor, 5=severe) used to weight penalties. |
| `repeat_issue_flag` | integer | `1` if GAO flagged recurring problems; `0` otherwise. |
| `recommendation_count` | integer | How many recommendations GAO issued in this finding. |
| `implemented_recs` | integer | Number of recommendations marked implemented/closed. |
| `open_recs` | integer | Remaining open or partially implemented recommendations. |
| `summary` | string | Short paraphrased description for ops and docs. |

The GAO findings table plugs into the V&V/repeat-offender penalty logic: map each `program_id` to `RdteModel.program_index`, convert `severity` and `repeat_issue_flag` into `PenaltyBook.bump` inputs, and log `finding_type` when computing policy multipliers (e.g., `contracting` gate should know if the finding was `compliance` vs. `cost`). Copy this schema into `data/stubs/gao_findings.csv` and replace it with your real GAO exports whenever they’re ready.

Example row:

```
GAO22-105123-F1,GAO-22-105123,2022,PRG-ISR-001,Joint ISR Fusion,10USC,MIP,ISR,Service,cost,4,1,3,1,2,"Persistent cost growth and inadequate estimation"
```
