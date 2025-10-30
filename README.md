# ABM: Adaptive RDT&E Transitions (DoD/IC)

This repository provides an Agent-Based Model (ABM) to explore how policy design, funding flexibility, and feedback latency shape the transition of defense innovations from RDT&E to field adoption.

Core idea: Compare a linear governance pipeline vs. an adaptive feedback governance model under normal operations and external shocks (e.g., continuing resolutions, cyber events), measuring transition rate, cycle time, feedback delay, resilience, and diffusion speed.

---

## Quick Start

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

## Knobs and Config

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

## Outputs and Metrics

- Results CSV with per-run aggregates (`results.csv`): transition_rate, avg_cycle_time, diffusion_speed, attempts, transitions.
- Metadata JSON (`metadata.json`) with all run parameters and base_seed.
- Per-run events CSVs (`events_run_<i>.csv`) logging attempt/legal/funding/contracting/test/adoption outcomes per tick.
- Quick plotting utility: `python -m src.viz --path outputs/.../results.csv` (saves `transition_rate_hist.png`).

---

## Files

- `src/model.py` — Mesa-style model class (`RdteModel`), scheduling, gates, event logging, loaders.
- `src/agents.py` — Agents and stage pipeline behavior.
- `src/policies.py` — Gate functions (legacy funding/oversight + stage-aware pipeline) with config hooks.
- `src/metrics.py` — MetricTracker, PenaltyBook, EventLogger.
- `src/run_experiment.py` — CLI runner; loads config; writes results/metadata/events.
- `src/viz.py` — Simple plotting.
- `parameters.yaml` — Tunables for gates, penalties, and data paths.
- `requirements.txt` — Dependencies.

---

## Changelog

### 2025-10-29

- Parameterized shock window duration and added `--shock_duration`.
- Removed redundant local RNG; rely on Mesa `Model.random`.
- Count attempts on prototype start (transition_rate meaningful).
- Added stage-gate pipeline (TRL, legal, funding color/source, contracting, tests).
- Added repeat-failure penalties by axis (researcher/domain/org/etc.).
- Wired labs and FY26 RDT&E CSVs; added small ecosystem bonus when labs present.
- Added per-run event logging (gate outcomes) and `--config` loader.

