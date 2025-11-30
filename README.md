# ABM: Adaptive RDT&E Transitions (DoD/IC)

This repository provides an Agent-Based Model (ABM) to explore how policy design, funding flexibility, and feedback latency shape the transition of defense innovations from RDT&E to field adoption.

Core idea: Compare a linear governance pipeline vs. an adaptive feedback governance model under normal operations and external shocks (e.g., continuing resolutions, world events), measuring transition rate, cycle time, feedback delay, resilience, and diffusion speed.

---

## Table of Contents

- [Overview](#overview)
- [Build & Run](#build--run)
- [Capabilities](#capabilities)
- [Current Limits](#current-limits)
- [Live Browser UI](#live-browser-ui)
- [VS Code Setup](#vs-code-setup)
- [Data Inputs](#data-inputs)
- [Data Schema Overview](#data-schema-overview)
- [Profiles & Modes](#profiles--modes)
- [Priors & Validation](#priors--validation)
- [Smoke Tests & Quick Runs](#smoke-tests--quick-runs)
- [Metrics & Logging](#metrics--logging)
- [Configuration](#configuration)
- [Schemas](#schemas)
- [Outputs](#outputs)
- [Repository Structure](#repository-structure)
- [Documentation Links](#documentation-links)
- [Changelog](#changelog)

---

## Overview

- Purpose: explore how governance regimes, funding colors, and shocks affect prototype transition and diffusion.
- Approach: agent-based model with a stage-gate pipeline (legal -> funding -> contracting -> tests -> adoption) and tunable gate logic.
- Outputs: per-run metrics (transition rate, cycle time, diffusion speed) and per-event logs for gate outcomes.

---

## Build & Run

1. Create and activate a venv
   - `python -m venv .venv`
   - Linux/macOS: `source .venv/bin/activate`
   - Windows: `.venv\Scripts\activate`

2. Install dependencies
   - `pip install -r requirements.txt`

3. Run experiments
   - Linear/Adaptive:
     - `python -m src.run_experiment --scenario linear   --runs 10 --steps 200 --seed 42`
     - `python -m src.run_experiment --scenario adaptive --runs 10 --steps 200 --seed 42`
   - Shock with explicit duration:
     - `python -m src.run_experiment --scenario shock --runs 10 --steps 200 --seed 42 --shock_at 80 --shock_duration 20`
- Use a custom config file (overrides parameters.yaml):
  - `python -m src.run_experiment --scenario adaptive --config my_params.yaml`
  - Agent behavior knobs now respect `parameters.yaml:agents.*` (prototype_rate, learning_rate, policymaker agility/rigidity, end-user thresholds).

**Smoke test (Mesa)** - run a short linear scenario to validate the new data stack before larger experiments:

```
python -m src.run_experiment --scenario linear --runs 1 --steps 20 --seed 45
```

Mesa's server (`python -m src.server --scenario adaptive`) still works with these inputs; just point `--config` or `parameters.yaml` at your entity/role CSVs plus the GAO/shock/vendor/collaboration sources before launching the GUI.

4. Inspect outputs
   - Results: `outputs/<scenario>_<timestamp>/results.csv`
   - Metadata: `outputs/<scenario>_<timestamp>/metadata.json`
   - Per-run events (gate outcomes): `outputs/<scenario>_<timestamp>/events_run_<i>.csv`
   - Quick plot: `python -m src.viz --path outputs/<scenario>_<timestamp>/results.csv`
---

## Windows Setup (Mesa)

Follow these steps on Windows PowerShell. This sets up Python, a virtual environment, Mesa, and runs a quick smoke test plus a static visualization.

- Prerequisites
  - Install Python 3.11+ from python.org or Microsoft Store. Verify: python -V
  - Optional (large CSVs): Git LFS - git lfs install

- Create and activate a virtual environment
  - python -m venv .venv
  - .venv\Scripts\Activate  (PowerShell)
  - Upgrade pip (recommended): python -m pip install --upgrade pip

 - Install dependencies
   - python -m pip install -r requirements.txt

 - Run a quick smoke test (writes to outputs/)
   - python -m src.run_experiment --scenario adaptive --runs 1 --steps 50 --seed 42
   - You may see warnings if data CSVs are not present locally (OK for a smoke test).

- Generate a simple visualization (PNG)
  - python -m src.viz --path outputs\adaptive_<timestamp>\results.csv
  - Produces: outputs\adaptive_<timestamp>\transition_rate_hist.png

- Data files (optional but recommended)
  - Place CSVs under data/ (or pass --labs_csv/--rdte_csv):
    - data\dod_labs_collaboration_hubs_locations.csv
    - data\FY2026_SEC4201_RDTandE_All_Line_Items.csv

- Troubleshooting
  - If venv activation is blocked: run PowerShell "as Administrator" and temporarily allow scripts:
    - Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
  - If python resolves to the wrong interpreter: try py -3.11 -m venv .venv then py -3.11 -m pip install -r requirements.txt.
  - If installs are slow or blocked by a proxy, set pip.ini proxy settings or use a corporate index.
  - If matplotlib needs a backend on headless servers, PNG output still works via Agg (already default for our usage).

---

## Live Browser UI

- Launch: `python -m src.server --host 127.0.0.1 --port 8521 --open-browser`
- What's new: refreshed "RDT&E Transition Lab" styling (CSS injected), KPI cards, stage-distribution pills, gate-context pills, and dual charts (adoptions + stage progression).
- Controls: sliders for population/funding/shock timing; dropdowns for regime/portfolio/service/org mix/funding pattern; `focus_researcher_id` to spotlight one project.
- Trends & detail:
  - Set `trend_start_tick` / `trend_end_tick` to view adoption counts and averages over a custom window (user-defined date/tick range).
  - Use `focus_program_id` (preferred) or `focus_researcher_index` + `UI mode = Advanced` to see full project fields (authority, funding, GAO penalty, vendor risk, capacities, classification).
  - Probability preview panel shows current vs. what-if transition probability (funding/contracting/test/adoption + overall) for the focused project. Adjust `what_if_quality_delta` to simulate improvements or degradations without mutating the live run.
  - Focus selection mode lets you pick `Random` (default), `Best`, `Worst`, or `Manual` to auto-select a project when the server starts.
- Data: UI reads live from the running model; event CSVs still land under `outputs/<scenario>_<timestamp>/events_run_<i>.csv` when using the CLI runner.

---

## Capabilities

- Stage-gate pipeline with TRL growth: Feasibility -> Prototype Demo -> Functional -> Vulnerability -> Operational test -> Adoption.
- Gates: legal review (favorable/caveats/unfavorable/not conducted), stage-aware funding with color/source behavior, contracting, and test gates.
- Policy alignment bias: small environmental-signal bonus based on alignment to Presidential/NDS/CCMD/Agency priorities.
- Shock modeling: configurable start (`--shock_at`) and duration (`--shock_duration`).
- Repeat-failure penalties: configurable system that penalizes "repeat offenders" across axes (researcher, domain, org_type, authority, funding_source, kinetic, intel, stage).
- Data inputs: optional labs/hubs CSV (ecosystem bonus) and FY26 RDT&E line items CSV (available for analysis/reporting).
- Metrics per run: transition rate, average cycle time, diffusion speed.

## Current Limits

- Simplified funding/oversight; no explicit queues/aging, portfolios, or reprogramming workflows.
- No collaboration network topology; agents act independently aside from coarse feedback.
- Utility/adoption uses a simple function (quality + environmental signal + small alignment/penalty bias).
- Single shock window per run; no multi-shock or stochastic shocks.
- Aggregate metrics only; use event CSVs for stage-by-stage analysis (enabled).

---

## Data Inputs

### Core Data Inputs

| Dataset | Default File | Purpose | Primary Keys |
| --- | --- | --- | --- |
| RDT&E Entities | `data/rdte_entities.csv` | Labs, program offices, IC orgs, service components, primes | `entity_id` |
| Program–Entity Roles | `data/program_entity_roles.csv` | Mapping of who sponsors, executes, tests, or operates a program | `program_id`, `entity_id` |
| Vendor Evaluations | `data/vendor_evaluations.csv` | CPARS-lite history: cost, schedule, tech, management, cyber | `vendor_id`, `program_id` |
| GAO Findings | `data/gao_findings.csv` | Oversight findings with severity, recommendations, repeat flags | `finding_id`, `program_id` |
| Labs Catalog | `data/labs.csv` | Physical labs, hubs, IC facilities, and vendor campuses | `lab_id` |
| Historical Outcomes | `data/closed_projects.csv` | Transitioned, canceled, and on-hold historical project records | `project_id`, `program_id` |
| FY26 RDT&E Template | `data/templates/rdte_funding_row_simulated.csv` | Synthetic PE-level FY26 funding data | `pe_number` |

### Required Minimum Inputs
- `data/rdte_entities.csv`
- `data/program_entity_roles.csv`
- `data/labs.csv`

All other datasets enhance fidelity but are optional.

### Behavioral Role of Each Dataset
- **RDT&E Entities + Program Roles**: define how sponsors, executors, testers, and operators influence program quality, timeline pressure, authority mix (10 USC, 50 USC, allied), capacity constraints, and cross-service/interagency friction.
- **Labs Catalog**: adds physical/geographic context (hubs, sector, specialization) for ecosystem bonuses and CONUS/OCONUS/allied experimentation effects.
- **Vendor Evaluations**: shape schedule slip, cost growth, technical success, and cyber-vulnerability penalties that flow into contracting/test gates.
- **GAO Findings**: drive oversight pressure, repeat-offender penalties, and governance mismatch risk by program/domain/authority/org type/funding source.
- **Historical Closed Projects**: provide empirical priors (transition, cancel, on-hold) by domain, authority mix, and vendor/GAO risk interactions; blended with in-simulation factors (researcher variance, alignment, shocks).
- **FY26 RDT&E Template**: analysis/reporting only by default; extend to seed program agents if desired.

### Historical outcomes baseline
`data/closed_projects.csv` supplies priors for transition vs. cancel/on-hold by domain, authority mix (10/50/ALLIED), vendor risk, and GAO severity history. Priors are softly blended into gate probabilities via `closed_priors_weight` and `prior_weights_by_gate` so current run conditions still dominate.

### Extended data (optional but supported)
- `data/shock_events.csv`: dated CRs/conflicts/policy changes to replay real-world shock timelines.
- `data/collaboration_network.csv`: collaboration edges to feed ecosystem/diffusion adjustments.

### CLI overrides and profiles
- CLI overrides: `--labs_csv` overrides `data.labs_locations_csv`; `--rdte_csv` overrides `data.rdte_fy26_csv`; `--config` loads an alternate YAML (CLI flags still win).
- Profiles: `parameters.yaml` (production realism), `parameters.demo.yaml` (fast/demo), `parameters.stressed.yaml` (conservative/shock). Override with `--config` or `--testing_profile`.
## Data Schema Overview

- Core CSVs are listed in the Core Data Inputs table above; populated examples now live under data/ (no stub paths) and can be swapped for real exports when ready.
- Field-by-field definitions are in the Glossary section; use data/templates/ for column guidance when building new sources.
- Pipeline: CSVs -> loaders -> program/entity/vendor/GAO metrics + historical priors -> gate probabilities (funding, contracting, test, adoption).
- Priors: closed_projects.csv feeds transition/cancel/on-hold priors by domain, authority mix, vendor risk bucket, GAO severity bucket, and program; blended via closed_priors_weight and prior_weights_by_gate (defaults 0.05 per gate; set to 0 to disable).
- Smoke/demo: python -m src.smoke_demo checks that demo-profile transitions > 0; set model.testing_profile: demo in YAML or --testing_profile demo for GUI smoke tests.

## Profiles & Modes
- Production (realism): `parameters.yaml` with conservative gate bases and lower prior weights (0.05/gate), `testing_profile: production`.
- Demo (fast/smoke): `parameters.demo.yaml` with looser gates and `testing_profile: demo` to force transitions quickly.
- Stressed/Shock: `parameters.stressed.yaml` for conservative/shock what-ifs.
- Override via CLI: `--config <file>` and optionally `--testing_profile production|demo`. Mesa UI also exposes testing_profile.

## Priors & Validation
- Priors toggle: `penalties.enable_priors` plus `closed_priors_weight` and `prior_weights_by_gate` control influence.
- Validation scripts: `python -m src.check_priors` reports coverage/overall rate; `python -m src.ci_regression` runs demo transitions>0, priors coverage, and a no-priors sanity check.
- Model/server log active profile, priors enabled/disabled, and prior weights at startup; warning if closed_projects is missing/empty.

## Smoke Tests & Quick Runs
- Demo smoke: `python -m src.smoke_demo` (asserts transitions > 0).
- Custom demo run: `python -m src.run_experiment --config parameters.demo.yaml --scenario adaptive --runs 1 --steps 80 --seed 123 --events`.
- Mesa UI: `python -m src.server --host 127.0.0.1 --port 8524 --open-browser` (use `--config parameters.demo.yaml` for demo). Header shows profile/prior status; Advanced view highlights overrides vs. baseline values.

## Metrics & Logging
- Run summaries include testing_profile, priors_enabled, prior_weights_by_gate, and gate pass/fail counts (aggregate and by stage).
- Gate pass/fail counts are also exposed in results for bottleneck analysis.
- Scenario levers: tune `gao_weight`, `vendor_weight`, and the authority/capacity values in the entity/roles CSVs to run sensitivity experiments.

---

## Configuration

- CLI flags
  - `--runs`, `--steps`, `--seed`, population sizes (`--n_researchers`, `--n_policymakers`, `--n_endusers`)
  - Funding weights: `--funding_rdte`, `--funding_om`
  - Scenario: `--scenario linear|adaptive|shock`
  - Event logging: `--events` (default) and `--no-events` control whether per-run gate CSVs are written.
  - Shocks: `--shock_at`, `--shock_duration`
  - Data paths: `--labs_csv`, `--rdte_csv`
  - Config file: `--config my_params.yaml`

- parameters.yaml
  - gates: parameterize funding/contracting/legal/test probabilities and adjustments
  - penalties: per-failure increment, caps, decay, axes by gate (funding/contracting/test/legal/adoption)
  - data: labs and RDT&E CSV paths (relative paths recommended)

---

## Schemas

JSON Schema definitions live under `schemas/` so you can keep the CSV inputs and outputs aligned with what the model actually reads and writes.

- `schemas/event_log.schema.json` captures the per-tick gate/event data written by `EventLogger` (`outputs/<scenario>_<timestamp>/events_run_<i>.csv`) and lists the probability-context fields (`gate_prob_*`, `legal_*`, `dependency_*`, etc.).
- `schemas/labs.schema.json` documents the optional lab/hub fields (`name/site/facility`, the latitude/longitude variants, `service`, `specializations`, and `region`) and mirrors the header of `data/templates/labs_template.csv`.
- `schemas/rdte_fy26.schema.json` describes the normalized FY26 line-item fields (`program_id`, `service_component`, funding identifiers, alignment scores, MBSE/digital maturity fields, dependencies, status flags, and so on) that `_load_rdte` stores on each researchers program context.
- `schemas/mbse.schema.json` defines the digital engineering supplement (`project_id`, `digital_maturity`, `model_coverage`, `simulation_runs`, `defect_escape_rate`, `twin_sync_level`) used by the optional MBSE template.

Copy the templates from `data/templates/` before running experiments to guarantee a known-good shape, and use whichever validator you prefer (for example, convert the CSV to JSON and run `jsonschema`, or simply inspect the headers) to confirm your data satisfies the documented properties.

---

## Outputs

- Results CSV with per-run aggregates (`results.csv`): transition_rate, avg_cycle_time, diffusion_speed, attempts, transitions.
- Metadata JSON (`metadata.json`) with all run parameters and base_seed.
- Use `--no-events` if you only need aggregate results and want to skip per-run gate CSVs.
- Per-run events CSVs (`events_run_<i>.csv`) logging attempt/legal/funding/contracting/test/adoption outcomes per tick.
- Quick plotting utility: `python -m src.viz --path outputs/.../results.csv` (saves `transition_rate_hist.png`).

---

## Repository Structure

- `src/model.py` - Mesa-style model class (`RdteModel`), scheduling, gates, event logging, loaders.
- `src/agents.py` - Agents and stage pipeline behavior.
- `src/policies.py` - Gate functions (legacy funding/oversight + stage-aware pipeline) with config hooks.
- `src/metrics.py` - MetricTracker, PenaltyBook, EventLogger.
- `src/run_experiment.py` - CLI runner; loads config; writes results/metadata/events.
- `src/viz.py` - Simple plotting.
- `parameters.yaml` - Tunables for gates, penalties, and data paths.
- `requirements.txt` - Dependencies.

---

## Documentation Links

- Data readme: `data/README.md`
- Configuration defaults: `parameters.yaml`
- Dependencies: `requirements.txt`
- Visualization helper: `src/viz.py`
- Experiment runner: `src/run_experiment.py`

---


### 2025-11-30

- Tightened agent/model typing so policy gates, metrics, and log_event are recognized; added a safe scheduler tick accessor in agents.
- Cleaned `evaluate_and_adopt` by removing unreachable legacy logic and clarified the policy gate delegation; instantiated the local RNG to match comments.
- Pruned README ingestion boilerplate and refreshed the Table of Contents to reflect the current sections.

### 2025-11-20

- Made gate progression more resilient: stage-age boosts for funding/contracting/test gates and a 0.4 penalty floor so runs keep moving; adoption rejections now retry from the final stage.
- Modernized the Mesa UI with injected CSS, KPI cards, stage-distribution pills, gate-context pills, and dual charts (adoptions + stage progression); documented launch steps.
- Agent behavior now respects `parameters.yaml:agents.*` (researcher prototype/learning rates, policymaker agility/rigidity, end-user thresholds) across CLI runs and the UI.
- Updated README with UI details, config notes, and refreshed next steps.

### 2025-11-18

- Added a `Schemas` section to the README that highlights the JSON Schema files so labs locations, FY26 RDT&E line items, MBSE inputs, and per-run event logs all have documented column expectations.
- Called out the `data/templates/` files as a known-good shape and reminded users to compare their CSVs against the schema definitions (or their own validation tooling) before running experiments.

### 2025-11-17

- Fixed the researcher stage/test path so failed-test penalties/logging only fire when the gate actually fails and stage success advances cleanly.
- Added a `--events`/`--no-events` CLI toggle to control per-run gate CSVs and documented how to use it in the configuration/output sections.
- Removed the unused `model.oversight_regime` key from `parameters.yaml` so the defaults stay aligned with the implemented knobs.

### 2025-11-04

- Mesa visualization GUI is now available (`src/server.py`); launch with `python -m src.server` (add `--port` and `--open-browser` as needed).
- Integrated `DataCollector` into the model for live charts (adoptions per tick, cumulative adoptions).
- Updated README with Live Browser UI, Windows setup, and VS Code interpreter guidance.
- Adjusted Mesa UI params for Mesa 2.2 (using `Slider`, `Choice`, `NumberInput`).
- Added port/host CLI flags and startup message; troubleshooting notes for firewall/port conflicts.

### 2025-11-03

- Restructured README with Overview, linked Table of Contents, Build & Run, Data Inputs, Configuration, Outputs, Repository Structure, and Documentation Links.
- Added GitHub Action to auto-generate/update the README ToC on push.
- Parameterized gate logic via `parameters.yaml:gates` (funding/test/legal/contracting), and passed config through the model.
- Implemented per-run event logging with probability context (base, penalty factor, final) and stage latency; added JSON schema for event rows.
- Integrated optional data loaders for Labs and FY26 RDT&E CSVs; created CSV templates and JSON schemas under `data/templates/` and `schemas/`.
- Enhanced researcher/project context (project_id, program_office, service_component, sponsor, prime_contractor) and included these in event logs.
- Improved seeding clarity (base_seed + per-run seed) and expanded run metadata.
- Cleaned legacy paths and docstring encoding artifacts; removed unreachable code in researcher loop.

### 2025-10-29

- Parameterized shock window duration and added `--shock_duration`.
- Removed redundant local RNG; rely on Mesa `Model.random`.
- Count attempts on prototype start (transition_rate meaningful).
- Added stage-gate pipeline (TRL, legal, funding color/source, contracting, tests).
- Added repeat-failure penalties by axis (researcher/domain/org/etc.).
- Wired labs and FY26 RDT&E CSVs; added small ecosystem bonus when labs present.
- Added per-run event logging (gate outcomes) and `--config` loader.

---

## Next Steps

- Calibrate gate weights and penalty floors to match realistic transition rates by regime and publish baseline presets in the UI/CLI.
- Add percentile cycle-time reporting and median capture to `metrics.summary()` for richer briefing stats.
- Validate CSV inputs against schemas during CLI runs and surface friendly errors in both CLI and GUI when files are missing or malformed.
- Extend the GUI with export buttons for recent events/metrics and a “rerun with new seed” quick action, plus concise inline help for controls.
- Add unit tests for gate math, penalty decay/floors, adoption retry behavior, and CLI flag parsing; wire a GitHub Actions smoke run.
---

## Assumptions

Self-reported modeling assumptions to make runs fast and comparable. Calibrate or relax as you add data.

- Stage pipeline and cadence
  - Five stages: feasibility -> prototype_demo -> functional_test -> vulnerability_test -> operational_test; adoption follows the last stage.
  - Gates are attempted once per tick; at most one stage advances per tick.
  - TRL increases by small, fixed increments on each stage pass.

- Adoption and utility
  - End users evaluate a 20% random sample of the population (at least 1) and adopt on simple majority.
  - Perceived utility is additive: intrinsic quality + environmental signal + small alignment/penalty bias.

- Policy regimes and shocks
  - Linear/adaptive/shock affect base probabilities and signals rather than hard constraints.
  - Shocks reduce probabilities during a fixed window; no multi-shock or stochastic shock process yet.

- Funding colors and sources
  - Early stages primarily use RDT&E; later stages use a mix of RDT&E and O&M/Proc according to a configurable weight.
  - Sources (POM/UFR/Partner/etc.) act as simple multipliers, not explicit queues (yet).

- Legal and contracting
  - Legal outcomes are drawn from a regime/domain/authority-tuned distribution; "unfavorable" halts the attempt.
  - Contracting success is a simple probability influenced by regime and org type (e.g., commercial benefits in adaptive).

- Penalties ("repeat offenders")
  - Failures accumulate by axes (e.g., researcher, domain, org_type) and multiply down gate probabilities. Optional decay.

- Data effects
  - Labs CSV adds a small +0.01 ecosystem bonus; FY26 RDT&E CSV now drives rich per-program behavior (service, BA, portfolio, support factors, digital maturity, alignment, dependencies) used by the gates.

- Randomness and independence
  - Mesa scheduler randomizes activation; runs are independent via base_seed + run offset.

---

## Weights & Sensitivities

This model exposes tunable weights in `parameters.yaml` (gates, penalties, and select behavior). Below are common knobs, why they exist, and what happens when you change them.

- Funding availability (stage-aware)
  - Keys: `gates.funding_base_*` (linear/adaptive/shock, early/late), `gates.color_weight_late_mix`
  - Justification: baseline budget access and color-of-money friction differ by regime and stage.
  - Effects:
    - Increase: more stage entries and passes -> higher transition_rate, shorter cycle times, higher diffusion.
    - Decrease: more stalls at funding -> longer cycle times, fewer adoptions.

- Test pass probabilities and TRL effects
  - Keys: `gates.test_base.{feasibility|prototype_demo|functional_test|vulnerability_test|operational_test}`, `gates.test_trl_bonus_per_level`, `gates.test_trl_bonus_cap`
  - Justification: stage difficulty and maturity gains drive progression.
  - Effects:
    - Raise `test_base` or TRL bonus: faster progression, shorter stage latency, more adoptions.
    - Lower: more retries and higher attrition in later stages.

- Domain/kinetic adjustments and regime modifiers
  - Keys: `gates.test_kinetic_penalty`, `gates.test_cyber_vuln_ops_penalty`, `gates.test_adaptive_bonus`, `gates.test_shock_penalty`
  - Justification: kinetic and late cyber/EW tests are harder; adaptive processes speed evaluation; shocks slow it.
  - Effects: penalties reduce pass rates at affected stages; adaptive bonus offsets friction.

- Legal review distribution and shifts
  - Keys: `gates.legal_dist.*`, `gates.legal_title50_shift`, `gates.legal_kinetic_shift`, `gates.legal_penalty_shift_cap`
  - Justification: authority and mission area shape legal risk; repeated failures should push toward caveats/unfavorable.
  - Effects: more "favorable" -> faster throughput; higher shift values -> more caveats/unfavorable, longer cycles.

- Contracting success
  - Keys: `gates.contracting_base.{GovLab|GovContractor|Commercial}`, `gates.contracting_adaptive_bonus`, `gates.contracting_linear_commercial_penalty`
  - Justification: vehicle/authority/process efficiency varies by org type and regime.
  - Effects: higher bases accelerate mid-pipeline; penalties slow commercial paths under linear governance.

- Repeat-failure penalties
  - Keys: `penalties.per_failure`, `penalties.max_penalty`, `penalties.decay`, `penalties.axes_by_gate`
  - Justification: persistent underperformance should reduce future success odds; decay allows recovery.
  - Effects:
    - Increase `per_failure`/`max_penalty`: sharper compounding penalties -> lower pass rates after repeated failures.
    - Increase `decay`: faster "forgiveness" -> penalties fade quicker.

- Behavior parameters (code defaults)
  - Researchers: `prototype_rate=0.05`, `learning_rate=0.1`
    - Higher `prototype_rate` -> more attempts; higher `learning_rate` -> faster quality recovery after rejections.
  - End-users: `adoption_threshold=0.6`
    - Lower threshold -> easier adoption; higher -> stricter adoption.
  - Environmental signal & alignment (code): adaptive +0.1, linear -0.05, shock -0.1; alignment bias +/-0.05; labs +0.01
    - Raise positive biases -> faster adoption; lower/negative -> slower.

Sensitivity testing tips
- Start with `runs=30-50`, `steps=200-300`, and adjust one group of weights at a time.
- Track median and percentiles of cycle time (add to metrics if needed) to see distributional effects, not just means.
- Use event CSVs to confirm which gate changes drive outcome shifts.

---

## Glossary

- **ABM (Agent-Based Model)** - Simulates individual researchers, policymakers, and end-users to surface how gate logic, funding, and adoption feedback create aggregate transition metrics.
- **RDT&E (Research, Development, Test & Evaluation)** - The lifecycle stage from prototyping through trials before programs flow into O&M; inputs to the ABM are the RDT&E line items and program attributes.
- **PE (Program Element)** - A DoD/IC funding bucket described in R-1 exhibits; we map the PE number into `program_id`/`Mapped_PE_Number` so researchers align with real programs.
- **BA (Budget Activity)** - High-level categories (BA2, BA3, BA4, etc.) that shape the starting gate (`feasibility`, `prototype_demo`, ) and funding priorities.
- **NDAA / Appropriations / R-1/R-2** - The legislative and comptroller documents that provide authoritative funding, mission, and maturity context for each PE; the ingestion workflow extracts these into schema fields.
- **Schema/Template Files** - JSON Schema files under `schemas/` and CSV templates under `data/templates/` capture the required columns so both synthetic and real data stay aligned with the loader expectations.
### Fields by Dataset (Glossary)

This glossary defines every field across all CSVs.

#### RDT&E Entities (data/rdte_entities.csv)
| Field | Definition |
| --- | --- |
| entity_id | Unique ID for lab, agency, office, IC element, vendor, FFRDC, or UARC. |
| name | Full entity name. |
| short_name | Abbreviated display name. |
| entity_category | Type: Lab, Agency, ProgramOffice, OperationalUnit, Vendor. |
| service | Army, Navy, USAF, USSF, CIA, NSA, NGA, DIA, DOE, etc. |
| parent_entity_id | Hierarchical owner, if applicable. |
| has_organic_rdte | 1 if the entity performs its own RDT&E. |
| rdte_roles | Roles such as sponsor, executing, test, ops. |
| base_budget_type | RDT&E, MIP, NIP, TOA, etc. |
| base_budget_pe | Program Element (PE) number. |
| base_budget_ba | Budget Activity (BA2-BA7). |
| estimated_rdte_capacity_musd | Estimated annual research capacity. |
| estimated_rdte_staff | Approximate personnel supporting RDT&E. |
| primary_domains | Mission areas: ISR, AI, GEOINT, CBRN, Space, EW, UAS. |
| authority_flags | Statutory authority: 10USC, 50USC, ALLIED. |
| location_region | CONUS-East, CONUS-West, NCR, INDOPACOM, EUCOM. |
| classification_band | Unclassified, Secret, TS/SCI. |
| notes | Additional context. |

#### Program-Entity Roles (data/program_entity_roles.csv)
| Field | Definition |
| --- | --- |
| program_id | ID of the RDT&E program. |
| entity_id | Entity participating in the program. |
| role | Sponsor, executing, test, ops, transition_partner. |
| effort_share | Relative magnitude of involvement (0-1). |
| note | Context or explanation. |

#### Vendor Evaluations (data/vendor_evaluations.csv)
| Field | Definition |
| --- | --- |
| evaluation_id | Unique evaluation record. |
| program_id | Program evaluated. |
| vendor_id | Unique vendor identifier. |
| vendor_name | Vendor name. |
| fiscal_year | FY of scoring. |
| cost_variance_pct | + if cost overran, - if underrun. |
| schedule_variance_pct | Schedule overrun or underrun. |
| technical_rating | Technical score (1-5). |
| management_rating | Management score (1-5). |
| cyber_findings_count | Security issues found. |
| major_breach_flag | 1 if a major breach occurred. |
| recompete_award_flag | Vendor competitive for follow-on work. |

#### GAO Findings (data/gao_findings.csv)
| Field | Definition |
| --- | --- |
| finding_id | Unique GAO finding ID. |
| report_id | GAO report number (GAO-XX-XXXXX). |
| report_year | Publication year. |
| program_id | Program affected. |
| program_name | Human-readable program name. |
| finding_type | Cost, schedule, performance, management, governance, security, etc. |
| severity | Impact scale (1-5). |
| repeat_issue_flag | 1 if problem also occurred in earlier years. |
| recommendation_count | Total GAO recommendations. |
| implemented_recs | Closed recommendations. |
| open_recs | Remaining open. |
| summary | Description of issue. |
| authority | 10USC, 50USC, MIP, NIP. |
| funding_source | RDT&E, TOA, MIP, NIP, etc. |
| domain | ISR, GEOINT, EW, AI, CBRN, Space. |
| org_type | Lab, vendor, agency, program office. |

#### Labs (data/labs.csv)
| Field | Definition |
| --- | --- |
| lab_id | Unique ID (aligned to entity_id or vendor_id). |
| name | Facility or organization name. |
| country | Country. |
| state | U.S. state or foreign province. |
| city | City / installation. |
| service_agency | Army DEVCOM, NRO, NSA, NGA, DOE, etc. |
| specialization | Technical areas (AI, EW, autonomy, SIGINT, etc.). |
| region | NCR, CONUS-East, CONUS-West, Pacific, EUCOM, etc. |
| funding_source | DoD RDT&E, DOE NNSA, NIP, MIP, private capital. |
| cross_service_agreements | Joint, interagency, allied, or consortia partnerships. |
| sector | Federal, FFRDC, UARC, Private. |

#### Historical Outcomes (data/closed_projects.csv)
| Field | Definition |
| --- | --- |
| project_id | Unique historical instance. |
| program_id | Program linked to historical variant. |
| program_name | Name of the program. |
| close_year | Year project closed. |
| close_status | Transitioned, Canceled, OnHold. |
| close_reason | Short rationale for outcome. |
| primary_domain | Mission area. |
| authority_flags | 10USC, 50USC, ALLIED. |
| sponsor_entity_id | Sponsor org. |
| executing_entity_id | Primary executor. |
| transition_partner_entity_id | Intended receiving org. |
| primary_vendor_id | Vendor responsible. |
| primary_vendor_name | Human-readable vendor name. |
| peak_rdte_funding_musd | Maximum annual funding. |
| total_duration_months | Duration of the variant. |
| funding_gate_successes | Passed funding milestones. |
| contracting_gate_successes | Passed contracting gates. |
| test_gate_successes | Passed DT/OT gates. |
| ops_eval_score | Operational evaluation (0-100). |
| gao_findings_count | Count of related GAO findings. |
| gao_avg_severity | Severity average. |
| vendor_avg_technical_rating | Mean vendor technical score. |
| vendor_avg_management_rating | Mean vendor management score. |
| max_cyber_findings | Maximum cyber issues. |
| notes | Freeform notes. |

#### FY26 RDT&E Template (data/templates/rdte_funding_row_simulated.csv)
| Field | Definition |
| --- | --- |
| pe_number | Program Element ID. |
| program_name | PE name. |
| service | Service or agency. |
| ba | Budget Activity. |
| fy26_request | FY26 funding amount. |
| fy25_enacted | Prior year amount. |
| _notes | Mapping or metadata notes. |
