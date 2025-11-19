ï»¿# ABM: Adaptive RDT&E Transitions (DoD/IC)

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
- [Next Steps](#next-steps-policy-lever-integration)
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
  - Optional (large CSVs): Git LFS â git lfs install

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
    - `data.labs_locations_csv: data/dod_labs_collaboration_hubs_locations.csv`
  - Effect: adds a small +0.01 "ecosystem support" bonus to environmental signal.

- FY26 RDT&E line items CSV (recommended to commit under `data/`)
  - parameters.yaml:
    - `data.rdte_fy26_csv: data/templates/rdte_funding_row_simulated.csv`
  - Effect: parsed into `model.rdte_fy26` for analysis; no behavioral change yet.
  - The richer `dod_rdte_funding_blocks_master.csv` file is now archived under `data/legacy/dod_rdte_funding_blocks_master.csv` for reference; the model no longer consumes it unless you explicitly point `--rdte_csv` at it after preprocessing.

- Overrides via CLI
  - `--labs_csv` and `--rdte_csv` override parameters.yaml.
  - `--config` loads an alternate YAML (CLI flags still override).

---

## Data Collection Strategy

The data collection strategy for the RDT&E transition simulation begins with constructing a comprehensive, schema-driven representation of the Defense and Intelligence RDT&E ecosystem, using publicly available NDAA language, Defense Appropriations Act tables, and R-1/R-2 justification documents as the authoritative foundation. The initial phase leans on a large set of realistic, structurally accurate synthetic entries that mirror how DoD and IC programs are organizedâcapturing Budget Activity codes, Program Element identifiers, mission focus areas, authority alignments, labs or contractors, team structures, technical maturity, and transition-relevant risk attributes. This simulated dataset delivers the diversity and coverage needed to prototype and validate the core agent-based model (ABM) behavior before real program data is introduced.

The second phase layers in targeted âR-1 liteâ ingestion, replacing a subset of synthetic entries with true program records sampled across Services and Agencies to improve fidelity where it matters mostâparticularly for mission-critical areas like ISR, cyber, space sensing, hypersonics, EW, and CBRNE. Each real-world entry is mapped into the established schema, with funding history, program stage, and technical descriptions extracted directly from R-1/R-2 documentation to calibrate maturity, risk scores, and cross-domain dependencies. As the model matures, the process expands into domain-focused ingestion (e.g., all missile defense or autonomy programs), enabling partial but meaningful grounding of the simulated portfolio in real fiscal and developmental structures.

Throughout, metadata flags track the provenance of each rowâdistinguishing synthetic placeholders, estimated values awaiting R-1 validation, and fully ingested program elementsâto keep data hygiene transparent and support sensitivity analysis. This staged approach lets the ABM evolve from a conceptually rich but synthetic environment into a calibrated simulation that reflects true transition dynamics while preserving the flexibility to deepen fidelity incrementally as additional R-1/R-2 data is incorporated.

---

## Technical Data Ingestion Workflow (RDT&E to ABM)

The data ingestion pipeline converts raw RDT&E program documentationâprimarily R-1 budget exhibits, R-2 Justification Books, NDAA line-item tables, and Defense Appropriations Act summariesâinto structured, simulation-ready entities for the ABM. The workflow begins by establishing a canonical schema that normalizes attributes across DoD, Defense Agencies, Intelligence Community elements, and dual-use programs, defining unique program identifiers, PE numbers, appropriations, Budget Activity codes, mission domains, authority alignments, execution organizations, technical maturity indicators, and dependency relationships.

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
- `schemas/rdte_fy26.schema.json` describes the normalized FY26 line-item fields (`program_id`, `service_component`, funding identifiers, alignment scores, MBSE/digital maturity fields, dependencies, status flags, and so on) that `_load_rdte` stores on each researcherâs program context.
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

- `src/model.py` â Mesa-style model class (`RdteModel`), scheduling, gates, event logging, loaders.
- `src/agents.py` â Agents and stage pipeline behavior.
- `src/policies.py` â Gate functions (legacy funding/oversight + stage-aware pipeline) with config hooks.
- `src/metrics.py` â MetricTracker, PenaltyBook, EventLogger.
- `src/run_experiment.py` â CLI runner; loads config; writes results/metadata/events.
- `src/viz.py` â Simple plotting.
- `parameters.yaml` â Tunables for gates, penalties, and data paths.
- `requirements.txt` â Dependencies.

---

## Documentation Links

- Data readme: `data/README.md`
- Configuration defaults: `parameters.yaml`
- Dependencies: `requirements.txt`
- Visualization helper: `src/viz.py`
- Experiment runner: `src/run_experiment.py`

---


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

## Next Steps (Policy Lever Integration)

- Flexible Funding Authorities
  - Add per-stage funding queues (by color) and a BA-8 "bridge"/reprogramming path with time cost and attrition.
  - Use FY26 RDT&E line items (`data/FY2026_SEC4201_RDTandE_All_Line_Items.csv`) to bias stage availability by portfolio.
  - Expose queue capacities, reprogramming delay, and priority rules in `parameters.yaml` and log queue wait times to events.

- Decentralized Experimentation
  - Associate researchers to nearest labs from `data/dod_labs_collaboration_hubs_locations.csv` and apply proximity benefits.
  - Increase `prototype_rate` and early-stage funding/test pass rates when co-located; allow lab-specific parameter sets.

- Dynamic Oversight (MBSE-enabled)
  - Introduce a `digital_maturity` attribute (from MBSE/digital-twin inputs) and add it as a positive modifier in `test_gate`.
  - Add optional `--mbse_csv`/`data.mbse_csv` loader and record digital evidence in event logs.

- Integrated Policy Feedback
  - Add multi-agency policymaker agents (DoD, IC, Congress) with distinct adaptation curves; aggregate cross-agency feedback.
  - Make scenario toggles to compare single-agency vs integrated loops and record adaptation metrics.

- Digital Engineering Integration
  - Leverage MBSE/digital-twin metrics across the pipeline to reduce legal/contracting friction and shorten test cycles when maturity is high.

- Live Browser UI clarity
  - Rename the Mesa UI sliders/inputs so they describe their function (agent cohorts, funding levels, governance regime, shock timing, random seed) and are easy to scan for broader audiences.
  - Consider adding inline helper text or hover tips describing what each control adjusts so visitors can explore without diving into the code first.

- Validation and CI
  - Add unit tests for gate math, penalties, stage/test failure handling, and CLI `--events`/`--no-events` toggles; add CSV schema validation for labs/RDT&E.
  - Wire a GitHub Actions workflow to run those tests plus a quick smoke run (e.g., `python -m src.run_experiment --scenario adaptive --runs 1 --steps 50`) so regressions surface before pushing.
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
  - Environmental signal & alignment (code): adaptive +0.1, linear -0.05, shock -0.1; alignment bias Â±0.05; labs +0.01
    - Raise positive biases -> faster adoption; lower/negative -> slower.

Sensitivity testing tips
- Start with `runs=30-50`, `steps=200-300`, and adjust one group of weights at a time.
- Track median and percentiles of cycle time (add to metrics if needed) to see distributional effects, not just means.
- Use event CSVs to confirm which gate changes drive outcome shifts.

---

## Glossary

- **ABM (Agent-Based Model)** â Simulates individual researchers, policymakers, and end-users to surface how gate logic, funding, and adoption feedback create aggregate transition metrics.
- **RDT&E (Research, Development, Test & Evaluation)** â The lifecycle stage from prototyping through trials before programs flow into O&M; inputs to the ABM are the RDT&E line items and program attributes.
- **PE (Program Element)** â A DoD/IC funding bucket described in R-1 exhibits; we map the PE number into `program_id`/`Mapped_PE_Number` so researchers align with real programs.
- **BA (Budget Activity)** â High-level categories (BA2, BA3, BA4, etc.) that shape the starting gate (`feasibility`, `prototype_demo`, â¦) and funding priorities.
- **NDAA / Appropriations / R-1/R-2** â The legislative and comptroller documents that provide authoritative funding, mission, and maturity context for each PE; the ingestion workflow extracts these into schema fields.
- **Schema/Template Files** â JSON Schema files under `schemas/` and CSV templates under `data/templates/` capture the required columns so both synthetic and real data stay aligned with the loader expectations.
