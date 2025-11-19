# Vendor / Program Evaluations Schema

| Field | Type | Description |
| --- | --- | --- |
| `evaluation_id` | string | Unique row identifier (e.g., `VE-2025-04-01`). |
| `program_id` | string | PE/program identifier linked to the researcher agent. |
| `vendor` | string | Contractor or laboratory performing execution. |
| `eval_date` | date | Evaluation timestamp. |
| `performance_score` | number | Score (0..100) summarizing delivery quality. |
| `reliability_score` | number | Score (0..100) representing schedule/reliability history. |
| `execution_notes` | string | Narrative capturing context (delays, cost overruns, successes). |
| `flag_followup` | boolean | `true` if the evaluator recommends corrective action (could feed penalties). |
| `focus_area` | string | Domain (e.g., `Cyber`, `Space`) or capability (e.g., `Autonomy`). |

Integrate vendor evaluations by feeding weighted scores into `ResearcherAgent.quality`, expanding `PenaltyBook` axes, or triggering additional `EventLogger` metadata. Use `flag_followup` to bump repeat-offender weights and have `performance_score` adjust `policy_gate` heuristics—e.g., degrade `test_gate` probabilities for lower-rated vendors or boost `adoption_gate` bias if a contractor is highly reliable.
