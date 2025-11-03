# ABM: Adaptive RDT&E Transitions (DoD/IC)

This repository provides an Agent-Based Model (ABM) to explore how policy design, funding flexibility, and feedback latency shape the transition of defense innovations from RDT&E to field adoption.

Core idea: Compare a linear governance pipeline vs. an adaptive feedback governance model under normal operations and external shocks (e.g., continuing resolutions, cyber events), measuring transition rate, cycle time, feedback delay, resilience, and diffusion speed.

---

## Table of Contents

- [Overview](#overview)
- [Build & Run](#build--run)
- [Data Inputs](#data-inputs)
- [Configuration](#configuration)
- [Outputs](#outputs)
- [Repository Structure](#repository-structure)
- [Documentation Links](#documentation-links)
- [Capabilities](#capabilities)
- [Current Limits](#current-limits)
- [Assumptions](#assumptions)
- [Weights & Sensitivities](#weights--sensitivities)
- [Next Steps](#next-steps-policy-lever-integration)
- [Changelog](#changelog)

---

## Overview

- Purpose: explore how governance regimes, funding colors, and shocks affect prototype transition and diffusion.
- Approach: agent-based model with a stage-gate pipeline (legal → funding → contracting → tests → adoption) and tunable gate logic.
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

## Capabilities

- Stage-gate pipeline with TRL growth: Feasibility → Prototype Demo → Functional → Vulnerability → Operational test → Adoption.
- Gates: legal review (favorable/caveats/unfavorable/not conducted), stage-aware funding with color/source behavior, contracting, and test gates.
- Policy alignment bias: small environmental-signal bonus based on alignment to Presidential/NDS/CCMD/Agency priorities.
- Shock modeling: configurable start (`--shock_at`) and duration (`--shock_duration`).
- Repeat-failure penalties: configurable system that penalizes “repeat offenders” across axes (researcher, domain, org_type, authority, funding_source, kinetic, intel, stage).
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
  - Effect: adds a small +0.01 “ecosystem support” bonus to environmental signal.

- FY26 RDT&E line items CSV (recommended to commit under `data/`)
  - parameters.yaml:
    - `data.rdte_fy26_csv: data/FY2026_SEC4201_RDTandE_All_Line_Items.csv`
  - Effect: parsed into `model.rdte_fy26` for analysis; no behavioral change yet.

- Overrides via CLI
  - `--labs_csv` and `--rdte_csv` override parameters.yaml.
  - `--config` loads an alternate YAML (CLI flags still override).

---

## Configuration

- CLI flags
  - `--runs`, `--steps`, `--seed`, population sizes (`--n_researchers`, `--n_policymakers`, `--n_endusers`)
  - Funding weights: `--funding_rdte`, `--funding_om`
  - Scenario: `--scenario linear|adaptive|shock`
  - Shocks: `--shock_at`, `--shock_duration`
  - Data paths: `--labs_csv`, `--rdte_csv`
  - Config file: `--config my_params.yaml`

- parameters.yaml
  - gates: parameterize funding/contracting/legal/test probabilities and adjustments
  - penalties: per-failure increment, caps, decay, axes by gate (funding/contracting/test/legal/adoption)
  - data: labs and RDT&E CSV paths (relative paths recommended)

---

## Outputs

- Results CSV with per-run aggregates (`results.csv`): transition_rate, avg_cycle_time, diffusion_speed, attempts, transitions.
- Metadata JSON (`metadata.json`) with all run parameters and base_seed.
- Per-run events CSVs (`events_run_<i>.csv`) logging attempt/legal/funding/contracting/test/adoption outcomes per tick.
- Quick plotting utility: `python -m src.viz --path outputs/.../results.csv` (saves `transition_rate_hist.png`).

---

## Repository Structure

- `src/model.py` — Mesa-style model class (`RdteModel`), scheduling, gates, event logging, loaders.
- `src/agents.py` — Agents and stage pipeline behavior.
- `src/policies.py` — Gate functions (legacy funding/oversight + stage-aware pipeline) with config hooks.
- `src/metrics.py` — MetricTracker, PenaltyBook, EventLogger.
- `src/run_experiment.py` — CLI runner; loads config; writes results/metadata/events.
- `src/viz.py` — Simple plotting.
- `parameters.yaml` — Tunables for gates, penalties, and data paths.
- `requirements.txt` — Dependencies.

---

## Documentation Links

- Data readme: `data/README.md`
- Configuration defaults: `parameters.yaml`
- Dependencies: `requirements.txt`
- Visualization helper: `src/viz.py`
- Experiment runner: `src/run_experiment.py`

---

## Changelog

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
  - Add per-stage funding queues (by color) and a BA-8 “bridge”/reprogramming path with time cost and attrition.
  - Use FY26 RDT&E line items (`data/FY2026_SEC4201_RDTandE_All_Line_Items.csv`) to bias stage availability by portfolio.
  - Expose queue capacities, reprogramming delay, and priority rules in `parameters.yaml` and log queue wait times to events.

- Decentralized Experimentation
  - Associate researchers to nearest labs from `data/dod_labs_collaboration_hubs_locations.csv` and apply proximity benefits.
  - Increase `prototype_rate` and early-stage funding/test pass rates when co-located; allow lab-specific parameter sets.

- Dynamic Oversight (MBSE‑enabled)
  - Introduce a `digital_maturity` attribute (from MBSE/digital‑twin inputs) and add it as a positive modifier in `test_gate`.
  - Add optional `--mbse_csv`/`data.mbse_csv` loader and record digital evidence in event logs.

- Integrated Policy Feedback
  - Add multi‑agency policymaker agents (DoD, IC, Congress) with distinct adaptation curves; aggregate cross‑agency feedback.
  - Make scenario toggles to compare single‑agency vs integrated loops and record adaptation metrics.

- Digital Engineering Integration
  - Leverage MBSE/digital‑twin metrics across the pipeline to reduce legal/contracting friction and shorten test cycles when maturity is high.

- Validation and CI
  - Add unit tests for gate math and penalties; add CSV schema validation for labs/RDT&E; wire a GitHub Actions workflow to run tests.
---

## Assumptions

Self-reported modeling assumptions to make runs fast and comparable. Calibrate or relax as you add data.

- Stage pipeline and cadence
  - Five stages: feasibility → prototype_demo → functional_test → vulnerability_test → operational_test; adoption follows the last stage.
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
  - Legal outcomes are drawn from a regime/domain/authority-tuned distribution; “unfavorable” halts the attempt.
  - Contracting success is a simple probability influenced by regime and org type (e.g., commercial benefits in adaptive).

- Penalties (“repeat offenders”)
  - Failures accumulate by axes (e.g., researcher, domain, org_type) and multiply down gate probabilities. Optional decay.

- Data effects
  - Labs CSV adds a small +0.01 ecosystem bonus; FY26 RDT&E CSV is ingested for analysis but not yet tied to funding.

- Randomness and independence
  - Mesa scheduler randomizes activation; runs are independent via base_seed + run offset.

---

## Weights & Sensitivities

This model exposes tunable weights in `parameters.yaml` (gates, penalties, and select behavior). Below are common knobs, why they exist, and what happens when you change them.

- Funding availability (stage-aware)
  - Keys: `gates.funding_base_*` (linear/adaptive/shock, early/late), `gates.color_weight_late_mix`
  - Justification: baseline budget access and color-of-money friction differ by regime and stage.
  - Effects:
    - Increase: more stage entries and passes → higher transition_rate, shorter cycle times, higher diffusion.
    - Decrease: more stalls at funding → longer cycle times, fewer adoptions.

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
  - Effects: more “favorable” → faster throughput; higher shift values → more caveats/unfavorable, longer cycles.

- Contracting success
  - Keys: `gates.contracting_base.{GovLab|GovContractor|Commercial}`, `gates.contracting_adaptive_bonus`, `gates.contracting_linear_commercial_penalty`
  - Justification: vehicle/authority/process efficiency varies by org type and regime.
  - Effects: higher bases accelerate mid-pipeline; penalties slow commercial paths under linear governance.

- Repeat-failure penalties
  - Keys: `penalties.per_failure`, `penalties.max_penalty`, `penalties.decay`, `penalties.axes_by_gate`
  - Justification: persistent underperformance should reduce future success odds; decay allows recovery.
  - Effects:
    - Increase `per_failure`/`max_penalty`: sharper compounding penalties → lower pass rates after repeated failures.
    - Increase `decay`: faster “forgiveness” → penalties fade quicker.

- Behavior parameters (code defaults)
  - Researchers: `prototype_rate=0.05`, `learning_rate=0.1`
    - Higher `prototype_rate` → more attempts; higher `learning_rate` → faster quality recovery after rejections.
  - End-users: `adoption_threshold=0.6`
    - Lower threshold → easier adoption; higher → stricter adoption.
  - Environmental signal & alignment (code): adaptive +0.1, linear −0.05, shock −0.1; alignment bias ±0.05; labs +0.01
    - Raise positive biases → faster adoption; lower/negative → slower.

Sensitivity testing tips
- Start with `runs=30–50`, `steps=200–300`, and adjust one group of weights at a time.
- Track median and percentiles of cycle time (add to metrics if needed) to see distributional effects, not just means.
- Use event CSVs to confirm which gate changes drive outcome shifts.
