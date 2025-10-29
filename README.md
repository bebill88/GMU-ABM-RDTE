# ABM: Adaptive RDT&E Transitions (DoD/IC)

This repository scaffolds an Agent-Based Model (ABM) to explore how **policy design**, **funding flexibility**, and **feedback latency** shape the transition of defense innovations from **RDT&E** to **field adoption**.

Built for quick iteration in **Visual Studio Code** with Python. Uses a clean, modular structure so you can extend agents, policies, and scenarios without rewriting the core engine.

> Core idea: Compare a **Linear Governance** pipeline vs. an **Adaptive Feedback** governance model under normal operations and **external shocks** (e.g., Continuing Resolutions, cyber events), measuring **transition rate, cycle time, feedback delay, resilience,** and **diffusion speed**.

---

## Quick Start

1. **Create and activate a venv (recommended):**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. **Install deps:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run an experiment:**
   ```bash
   python -m src.run_experiment --scenario adaptive --runs 10 --steps 200 --seed 42
   ```

4. **Inspect outputs:** CSVs land in `./outputs/` with run metadata and metrics. You can also visualize with `python -m src.viz`.

---

## Concept → Code Mapping (Codex-Readable)

- **Agents**
  - `ResearcherAgent`: produces prototypes; seeks funding; learns from feedback.
  - `PolicymakerAgent`: allocates funding; applies oversight; can adapt rules.
  - `EndUserAgent`: evaluates utility; generates feedback; decides adoption.
- **Environment**
  - Encodes **funding colors** (RDT&E vs. O&M/Procurement), **oversight regime** (linear vs. adaptive), and **external shocks**.
- **Scenarios (`src/policies.py`)**
  - `linear`: centralized control, rigid milestones, slow feedback.
  - `adaptive`: decentralized experimentation, rolling evaluations, faster feedback (e.g., OTA-like behavior).
  - `shock`: injects disruptions (CR delays, cyber events) to test resilience.
- **Metrics (`src/metrics.py`)**
  - `transition_rate`: % of prototypes that transition to acquisition/field.
  - `cycle_time`: ticks from prototype start to field adoption.
  - `feedback_delay`: lag from field signal to policy/funding response.
  - `resilience_index`: speed of recovery after a shock.
  - `diffusion_speed`: rate of adoption across “services/communities”.
- **Experiment driver (`src/run_experiment.py`)**
  - Defines parameters, seeds runs, logs metrics, writes CSVs.
- **Extensible config**
  - `src/parameters.yaml` holds defaults. Override via CLI or env vars.

---

## Files

- `src/model.py` — Mesa-style model class (`RdteModel`), schedules, step loop.
- `src/agents.py` — Agent classes + behaviors (researcher, policymaker, end-user).
- `src/policies.py` — Governance regimes, shock injectors, and policy levers.
- `src/metrics.py` — Metric calculators and online trackers.
- `src/run_experiment.py` — CLI experiment runner; writes outputs.
- `src/viz.py` — Simple matplotlib plots for results in `outputs/`.
- `src/utils.py` — Helpers (random, logging, timers, seeding, IO).
- `parameters.yaml` — Tunables for agents, funding, and policy rules.
- `requirements.txt` — Python dependencies.
- `.vscode/settings.json` — VS Code linting/formatting defaults.
- `.gitignore` — Python, VS Code, and data ignores.

---

## Design Notes

- **Neutral and testable**: keep policy levers and funding rules modular so you can A/B them in isolation.
- **No hard-coded truths**: parameters are explicit; behaviors are observable via logs/metrics.
- **Fast iteration**: default to small populations and short runs; scale up once stable.
- **Reproducibility**: seed runs; store configs and hashes in `outputs/metadata.json`.

---

## Next Steps (Suggested)

- Implement richer funding queues (BA 8 bridge funds, reprogramming agility).
- Add **network topologies** to reflect inter-service collaborations.
- Log **per-prototype trajectories** for detailed cycle-time histograms.
- Integrate **MBSE/digital twin stubs** (data-in, policy-out) for rolling evaluations.
