# ABM: Adaptive RDT&E Transitions (DoD/IC)

This repository provides an Agent-Based Model (ABM) to explore how policy design, funding flexibility, and feedback latency shape the transition of defense innovations from RDT&E to field adoption.

Core idea: Compare a linear governance pipeline vs. an adaptive feedback governance model under normal operations and external shocks (e.g., continuing resolutions, world events), measuring transition rate, cycle time, feedback delay, resilience, and diffusion speed.

---

## Table of Contents

- [Overview](#overview)
- [Build & Run](#build--run)
- [Data Inputs](#data-inputs)
- [Data Collection Strategy](#data-collection-strategy)
- [Technical Data Ingestion Workflow (RDT&E to ABM)](#technical-data-ingestion-workflow-rdte-to-abm)
- [Configuration](#configuration)
- [Schemas](#schemas)
- [Outputs](#outputs)
- [Repository Structure](#repository-structure)
- [Documentation Links](#documentation-links)
- [Capabilities](#capabilities)
- [Current Limits](#current-limits)
- [Assumptions](#assumptions)
- [Weights & Sensitivities](#weights--sensitivities)
- [Glossary](#glossary)
- [Next Steps](#next-steps)
- [Changelog](#changelog)
- [Live Browser UI](#live-browser-ui)
- [VS Code Setup](#vs-code-setup)

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

- Labs/hubs locations CSV (recommended to commit under `data/`)
  - parameters.yaml:
    - `data.labs_locations_csv: data/templates/labs_template.csv`
  - Effect: adds a small +0.01 "ecosystem support" bonus to environmental signal. The template now carries a richer lab list (service/region/specialization). If lat/lon are absent but city/state are present, the model assigns deterministic pseudo-coordinates so map displays still work.
  - Profiles: set `model.testing_profile: demo` in `parameters.yaml` to make short smoke tests transition (higher prototype rate, softened penalties). Keep `production` for normal runs.

- FY26 RDT&E line items CSV (recommended to commit under `data/`)
  - parameters.yaml:
    - `data.rdte_fy26_csv: data/templates/rdte_funding_row_simulated.csv`
  - Effect: parsed into `model.rdte_fy26` for analysis; no behavioral change yet.
  - The richer `dod_rdte_funding_blocks_master.csv` file is now archived under `data/legacy/dod_rdte_funding_blocks_master.csv` for reference; the model no longer consumes it unless you explicitly point `--rdte_csv` at it after preprocessing.

- Overrides via CLI
  - `--labs_csv` and `--rdte_csv` override parameters.yaml.
  - `--config` loads an alternate YAML (CLI flags still override).

- Extended data sources
  - `parameters.yaml` now exposes:
    - `data.gao_findings_csv` (GAO oversight & repeat-offender penalties)
    - `data.shock_events_csv` (CRs, conflicts, policy shocks)
    - `data.program_vendor_evals_csv` (CPARS-lite vendor/performance records)
    - `data.collaboration_network_csv` (lab/MOU graph edges feeding ecosystem bonuses)
    - `data.rdte_entities_csv` (expanded master list of RDT&E/IC entities)
    - `data.program_entity_roles_csv` (program→entity mappings with effort shares)
  - Use the stub files under `data/stubs/` until your actual exports are ready; each schema doc under `docs/` explains the expected headers.

---

## Data Schema Overview

- `data/stubs/gao_findings.csv` – GAO findings per program (severity, repeat flags, recommendations).
- `data/rdte_entities.csv` – master list of RDT&E/IC entities keyed by `parent_entity_id`.
- `data/program_entity_roles.csv` – program→entity mappings with roles and effort shares.
- `data/stubs/vendor_evaluations.csv` – multi-year vendor evaluations per program/vendor.
- `data/closed_projects.csv` – historical closed/transitioned projects with outcomes, GAO/vendor stats, and gate successes.

### GAO Findings Data
- Path: `data/stubs/gao_findings.csv` (replace with real exports when ready).
- Columns: `finding_id,report_id,report_year,program_id,program_name,finding_type,severity,repeat_issue_flag,recommendation_count,implemented_recs,open_recs,summary,authority,funding_source,domain,org_type`.
- Aggregation: per-row risk = `severity * (1 + repeat_issue_flag) * (0.5 + 0.5 * open_recs/recommendation_count)`; program scores are summed then normalized to [0,1].
- Model hook: stored on each program as `gao_penalty`; gates call `apply_gao_modifier(base_prob)` and scale by `gao_weight` (see `parameters.yaml:penalties.gao_weight`).

### RDTE Entities Schema
- Path: `data/rdte_entities.csv` keyed by `parent_entity_id` (treated as `entity_id` in the model).
- Columns: `parent_entity_id,has_organic_rdte,rdte_roles,base_budget_type,base_budget_pe,base_budget_ba,estimated_rdte_capacity_musd,estimated_rdte_staff,primary_domains,authority_flags,location_region,classification_band,notes`.
- Use: loader attaches entity attributes (capacity, domains, authorities, classification) to program-role mappings to modulate gate odds.

### Program–Entity Roles
- Path: `data/program_entity_roles.csv` with header `program_id,entity_id,role,effort_share,note`.
- Roles are grouped per program into `sponsor`, `executing`, `test`, `ops`, `transition_partner` (plus any extra role labels).
- Worked example (PRG-ISR-001): `sponsor`=SRV-ARMY-AFC-ISR, `executing`=LAB-NAVY-NRL-ISR & LAB-AFRL-RIO-ISR, `test`=UNIT-AF-ISRGRP-01, `ops`=UNIT-USMC-INTBN-01, `transition_partner`=AGY-DIA-TECH.
- Model hook: sponsor authority boosts funding odds; executing/test capacity and domain alignment lift contracting/test gates; classification bands add mild penalties when high-side coordination is required.

### Vendor Evaluations
- Path: `data/stubs/vendor_evaluations.csv` (header `evaluation_id,program_id,vendor_id,vendor_name,fiscal_year,cost_variance_pct,schedule_variance_pct,technical_rating,management_rating,cyber_findings_count,major_breach_flag,recompete_award_flag`).
- Aggregation: per-evaluation risk blends cost/schedule variance, technical/management ratings, cyber findings, and breach flags; averaged per `(program_id, vendor_id)` then normalized to [0,1].
- Model hook: stored as `perf_penalty` and applied most strongly to contracting gates; `vendor_weight` in `parameters.yaml` tunes sensitivity.

### How the ABM Uses These Data
- Pipeline: CSVs → loaders → per-program GAO penalty + per-program/vendor risk + role metrics → gate probabilities (`funding`, `contracting`, `test`, `adoption`).
- Role metrics: sponsor authority, executing/test capacity, domain alignment, and classification band feed multipliers inside the gates.
- GAO severity/repeat issues lower gate odds via `apply_gao_modifier`; vendor risk primarily reduces contracting success; entity capacity/authority mix nudges funding/test performance.
- Historical priors: `closed_projects.csv` feeds empirical transition-rate priors by domain, authority mix, vendor risk bucket, GAO severity bucket, and program; gates blend these as a mild multiplier (0.5–1.0) so past outcomes nudge but don’t dominate current probabilities.
- Prior weights: defaults set to 0.2 per gate in `penalties.prior_weights_by_gate`; adjust up/down to change historical influence or set to 0 to disable.
- Smoke/demo: `python -m src.smoke_demo` runs a short demo-profile check and asserts transitions > 0 (good for CI); set `model.testing_profile: demo` for GUI smoke tests.
- Profiles: use `parameters.yaml` for production realism, `parameters.demo.yaml` for fast/demo runs, and `parameters.stressed.yaml` for conservative/shock-style scenarios. Override via `--config` or `--testing_profile`.
- Scenario levers: tune `gao_weight`, `vendor_weight`, and the authority/capacity values in the entity/roles CSVs to run sensitivity experiments.

---

## Data Collection Strategy

- We build a comprehensive picture of the Defense and Intelligence RDT&E ecosystem by normalizing NDAA language, Defense Appropriations Act tables, and R-1/R-2 justification documents into a canonical schema. The initial phase relies on synthetic, structurally accurate entries so we can calibrate the agent-based model before real programs are introduced.
- The second phase stitches in targeted R-1-lite records, substituting synthetic placeholders with sampled programs across Services and Agencies (ISR, cyber, hypersonics, EW, CBRNE, etc.) for higher-fidelity coverage. Real entries are mapped with funding history, stage, and maturity context directly from those documents.
- Metadata flags keep provenance visible (synthetic placeholder, R-1 pending, fully ingested), so analysts can surface sensitivity and hygiene for each row.
- The ingestion pipeline converts R-1 exhibits, R-2 Justification Books, NDAA line tables, and Defense Appropriations Act summaries into structured rows that define program identifiers, PE numbers, appropriations, BAs, mission domains, authority alignments, execution organizations, maturity indicators, and dependencies.

---

## Technical Data Ingestion Workflow (RDT&E to ABM)

The data ingestion pipeline converts raw RDT&E program documentation-primarily R-1 budget exhibits, R-2 Justification Books, NDAA line-item tables, and Defense Appropriations Act summaries-into structured, simulation-ready entities for the ABM. The workflow begins by establishing a canonical schema that normalizes attributes across DoD, Defense Agencies, Intelligence Community elements, and dual-use programs, defining unique program identifiers, PE numbers, appropriations, Budget Activity codes, mission domains, authority alignments, execution organizations, technical maturity indicators, and dependency relationships.

1. **Source Acquisition & Parsing**  
   R-1/R-2 PDFs are pulled from official `.mil`, comptroller, or congressional sites, converted to machine-readable text (with OCR where necessary), and segmented into document fragments that isolate PE titles, BA classification blocks, funding tables, program descriptions, milestone schedules, and contractor/lab references. Every fragment is stored with timestamped version control for traceability.

2. **Field Extraction & Mapping**  
   Regex-based extractors and domain-specific NLP classifiers map raw text into schema fields: PE number -> `Mapped_PE_Number`, title -> `Program_Name`, appropriation/BA/service -> `Agency`, `Service_Component`, `Budget_Activity`, fiscal tables -> `FYXX_Actual/Enacted/Request`, and R-2 narrative -> inferred mission focus, intel discipline, technical maturity, and dependency counts tied to JADC2, ISR, EW, CBRNE, and autonomy ontologies. Extractors tag each attribute with a confidence score and flag low-confidence values for analyst review.

3. **Entity Consolidation & Deduplication**  
   Programs spanning multiple volumes or subprojects are consolidated into unified entries. Duplication checks rely on PE IDs, title similarity, and mission-aligned clustering. Entries are labeled as `R1_INGESTED`, `R1_R2_INGESTED`, or `ESTIMATE_ONLY_R1_PENDING` depending on how much real data replaces synthetic placeholders.

4. **Enrichment & Derivation**  
   Additional ABM-relevant scores are derived dynamically: `Transition_Risk_Index` (from BA, maturity, and integration complexity), `Mission_Criticality_Score` (from DoD priority tags and NDAA language), `Network_Centrality_Score` (from shared contractors/labs and funding co-occurrence), `Supply_Chain_Risk_Level` (from sector and vendor concentration), and `Innovation_Leverage_Factor` (from historical spillover patterns). These latent factors augment the ABM beyond the explicit R-1/R-2 fields.

5. **Validation, Hygiene, and Error Checking**  
   Entries undergo structural validation (BA matches PE, authority alignment obeys Title 10/50 rules, funding series show monotonicity), with missing/null fields flagged for remediation. Cross-dataset checks ensure consistency between Services, Defense Agencies, and Intelligence Community portfolios, and conflicts are logged for analysts.

6. **Export to Simulation-Ready Format**  
   Finalized rows export to a consolidated CSV or table where each entry = one RDT&E program agent, columns include static and dynamic attributes used by the ABM, and provenance flags keep the synthetic -> semi-validated -> fully ingested lineage. This dataset becomes the ABM's initial conditions for modeling transition success, budget shocks, cross-domain dependency propagation, and RDT&E-to-O&M flow dynamics.

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

## Supplementary Data Integration

External inputs such as GAO findings, shock events, vendor evaluations, and collaboration ecosystem records should be documented via `docs/schema_*.md` and seeded with stub CSVs under `data/stubs/`. Wire them into the Mesa model as follows:

1. **GAO findings (`docs/schema_gao_findings.md`)** - Preload the CSV each run, map `program_id` into `RdteModel.program_index`, and use `severity`/`repeat_offender` to bump `PenaltyBook.counts` so the per-gate penalties degrade `funding`/`test` probabilities for flagged programs.
2. **Shock events (`docs/schema_shock_events.md`)** - Treat each row as a scheduled perturbation: when the current tick falls between `start_tick` and `start_tick + duration`, scale `funding_rdte`/`funding_om` by `budget_impact` and emit metadata through `EventLogger` to tie gate outcomes to the shock type.
3. **Vendor/program evaluations (`docs/schema_vendor_evaluations.md`)** - Fold `performance_score`/`reliability_score` into `ResearcherAgent.quality` adjustments or gate multipliers, and trigger `PenaltyBook.bump` if `flag_followup` is `true` so low-performing contractors become repeat-offender cases.
4. **Collaboration network (`docs/schema_collaboration_network.md`)** - Ingest the edge rows that connect labs, services, vendors, and agencies. Build node-centrality scores from `intensity`-weighted edges, feed the resulting `ecosystem_support`/`innovation_leverage_factor`, and use the linkage to bias `network_centrality_score` when matching researchers to labs/vendors.

Run-time loaders should live near `_load_labs`/`_load_rdte` in `src/model.py`; add CLI options or parameter overrides that point to the real CSVs when you move beyond the `data/stubs/` placeholders. The new `docs/data_schema.md` shows how `entity_id`/`program_id` serve as the canonical keys across GAO, vendor, shock, collaboration, and organization tables, and `docs/schema_rdte_entities.md` describes the entity master list (`data/rdte_entities.csv`) that feeds `data/program_entity_roles.csv`. Validating the inputs with `jsonschema` or header inspections before a run keeps the pipelines stable.

### Entity integration pattern

1. **Load the entity tables during model init**  
   ```python
   entities = pd.read_csv("data/rdte_entities.csv")
   prog_roles = pd.read_csv("data/program_entity_roles.csv")
   entities_by_id = {row["entity_id"]: row for _, row in entities.iterrows()}
   program_to_entities = defaultdict(list)
   for _, link in prog_roles.iterrows():
       program_to_entities[link["program_id"]].append(link.to_dict())
   model.entities_by_id = entities_by_id
   model.program_to_entities = program_to_entities
   ```
2. **Attach org links to each program agent**  
   When a program row maps to researchers, derive `sponsor_entities`, `executing_entities`, `test_entities`, `ops_entities`, and a `primary_entity_id` (largest `effort_share`) so every program knows which org owns which role. Those entity IDs already feed GAO, vendor, collaboration, and shock tables.
3. **Gate logic can consume entity metadata**  
   Look up `primary_entity_id` in `entities_by_id` during `funding_gate`/`test_gate`, use its `base_budget_type`/`base_budget_ba`/`service`/`authority_flags` to select CR or BA-specific modifiers, apply the ecosystem bonus for well-connected nodes, and cap probabilities if an entity's `estimated_rdte_capacity_musd` or `estimated_rdte_staff` is shared among many programs.
4. **Plain-language summaries for non-ABM readers**  
   - `rdte_entities.csv` = "Who actually does the work" (org roster for services, program offices, labs, agencies with budget/domains).  
   - `program_entity_roles.csv` = "Who owns which program" (mapping of programs to sponsoring/executing/test/ops roles plus effort shares).

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

- Calibration & baselines
  - Calibrate gate weights and penalty floors to target realistic transition rates by regime; publish baseline presets for linear/adaptive/shock in the UI.
  - Add percentile cycle-time reporting and default demo presets to speed briefings.

- Data richness
  - Extend loaders to pull MBSE/digital maturity and lab proximity into gate modifiers; write these signals to event logs.
  - Validate CSVs against schemas during CLI runs and surface friendly errors in the GUI when files are missing/mis-shaped.

- UX polish
  - Add export buttons in the GUI for the latest events/metrics and a "rerun with new seed" quick action.
  - Add inline help/hover tips for sliders and dropdowns plus a focused-project mini-timeline (stage/gate outcomes).

- Quality gates
  - Add unit tests for gate math, penalty decay/floors, adoption retry behavior, and CLI flag parsing; wire a GitHub Actions smoke run.
  - Capture median/percentile cycle times and basic shock recovery metrics in `metrics.summary()`.
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

- <img width="1112" height="902" alt="image" src="https://github.com/user-attachments/assets/b3dd07f2-2f37-45f1-b860-cf2b1f85a51a" />

