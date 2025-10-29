# Quick Guide: Adaptive RDT&E ABM (V1)

Date: 2025-10-29

## What This Model Can Do

- Simulate RDT&E-to-field transitions with three governance regimes: `linear`, `adaptive`, `shock`.
- Capture funding and oversight effects via policy gates (`src/policies.py`).
- Track decision-relevant metrics per run: transition rate, average cycle time, diffusion speed.
- Explore the effect of shocks with configurable start (`--shock_at`) and duration (`--shock_duration`).
- Save reproducible outputs per experiment run batch: `outputs/<scenario>_<timestamp>/{results.csv, metadata.json}`.
- Provide a quick plot of transition-rate distribution from a results CSV (`src/viz.py`).

## What It Does Not Do (Current Limits)

- Not calibrated to empirical program data; outputs are comparative/illustrative.
- Simplified funding/oversight: no queues, portfolios, or true multi-color appropriations.
- No network topology or collaboration graph; agents act independently aside from coarse feedback.
- Utility/adoption is a simple additive function of prototype quality and a regime-dependent signal.
- Single shock window per run (start/duration); no multiple or stochastic shock processes.
- Limited metrics in CSV aggregate; no per-prototype event log (starts, gate outcomes, adoption ticks).
- No built-in config loader for `parameters.yaml` yet (CLI flags control runs).

## How To Run Experiments

1) Setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
```

2) Run

```bash
# Linear / Adaptive examples
python -m src.run_experiment --scenario linear   --runs 10 --steps 200 --seed 42
python -m src.run_experiment --scenario adaptive --runs 10 --steps 200 --seed 42

# Shock with explicit shock duration
python -m src.run_experiment --scenario shock --runs 10 --steps 200 --seed 42 \
  --shock_at 80 --shock_duration 20
```

3) Inspect outputs

- CSV: `outputs/<scenario>_<timestamp>/results.csv`
- Metadata: `outputs/<scenario>_<timestamp>/metadata.json`
- Quick plot:

```bash
python -m src.viz --path outputs/<scenario>_<timestamp>/results.csv
```

## Knobs You Can Turn (and Expected Effects)

CLI flags (see `src/run_experiment.py:73`):

- `--runs` (int): number of independent runs; increases statistical stability.
- `--steps` (int): simulation ticks per run; longer runs allow more attempts/transitions.
- `--seed` (int): base seed; the script increments per run for independence.
- `--n_researchers` / `--n_policymakers` / `--n_endusers` (int): population sizes; more researchers generally increases attempts/adoptions.
- `--funding_rdte` / `--funding_om` (float): normalized weights; higher values increase funding availability in gates.
- `--scenario` (`linear|adaptive|shock`): picks the regime; `adaptive` accelerates via positive environmental signal and policy adaptation; `shock` introduces headwinds during the window.
- `--shock_at` (int): tick when the shock starts.
- `--shock_duration` (int): number of ticks the shock persists (see `src/model.py:42,55,131`).

Code-level parameters (edit and rerun):

- Agent behavior defaults in `src/model.py` constructor when creating agents:
  - Researchers: `prototype_rate=0.05`, `learning_rate=0.1` (see `src/model.py:64`).
  - Policymakers: `allocation_agility=0.1`, `oversight_rigidity=0.8` (see `src/model.py:71`).
  - End users: `adoption_threshold=0.6`, `feedback_strength=0.4` (see `src/model.py:78`).
  - Effects: higher `prototype_rate` increases attempts; higher `learning_rate` shortens cycle time after rejections; lower `oversight_rigidity` raises oversight pass probability; lower `adoption_threshold` increases adoptions.

- Policy gates in `src/policies.py`:
  - `funding_gate(...)` mixes regime and funding weights to set pass probability (see `src/policies.py:18`).
  - `oversight_gate(...)` mixes regime rigidity and prototype quality (see `src/policies.py:38`).
  - Effects: increasing `funding_rdte`/`funding_om` boosts funding pass rates; reducing effective rigidity or increasing quality improves oversight pass rates.

- Environment signal in `src/model.py`:
  - `environmental_signal()` adds +0.1 for `adaptive`, -0.05 for `linear`, and -0.1 during `shock` (see `src/model.py:92`).
  - Effects: positive signal raises perceived utility, increasing adoption likelihood.

- Adoption evaluation in `src/model.py`:
  - `evaluate_and_adopt(...)` samples ~20% of end users and uses simple majority (see `src/model.py:109`).
  - Effects: larger samples make adoption thresholds stricter; modifying the rule can speed/slow diffusion.

Note: `parameters.yaml` documents intended tunables but is not yet wired into the CLI. Use CLI flags or edit the code points above.

## Outputs and Metrics

- `transition_rate`: transitions / attempts (attempts counted when researchers start a prototype).
- `avg_cycle_time`: average ticks from prototype start to adoption (only for those that transitioned).
- `diffusion_speed`: average adoptions per tick.

## Recommended Experiment Patterns

- Compare regimes with identical seeds and populations; vary one factor at a time.
- Sensitivity sweeps: e.g., `--funding_rdte` from 0.3 → 1.2; `--oversight_rigidity` in code 0.8 → 0.3.
- Shock robustness: vary `--shock_at` and `--shock_duration` to assess resilience and recovery.

## Where To Extend Next

- Add a config loader to use `parameters.yaml` with CLI override precedence.
- Log per-prototype events (attempts, gate outcomes, adoption ticks) for richer analytics.
- Introduce network topology and heterogeneous policymakers/end-users.
- Add more plots (cycle-time histograms, adoption curves over time).

