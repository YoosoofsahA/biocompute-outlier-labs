# AGENTS.md

Guidance for coding agents (Claude Code, Codex, Cursor and others) working in this repo.

## Project: Fresh Eyes

A hybrid spoilage detector built at Biocomputing Hack London (3 Nov 2026). Silicon (ordinary code) finds shapes:
an edge detector catches mould spots. A simulated dish of neurons gets used to fresh colour and responds strongly
when the colour changes, catching early browning. Neither half needs labelled photos of rotten food.

**Read [`fresh-eyes-spec.md`](fresh-eyes-spec.md) before writing any code. It is the source of truth.** If the code
and the spec disagree, stop and tell the human; don't silently pick one.

Everything runs on the Cortical Labs `cl` SDK simulator, using the leaky integrate-and-fire (LIF) network in
`src/organoid_simulator/`. The dish code must also run unchanged on a real CL1.

## Setup and running

```bash
uv sync                                               # Python 3.13, cl-sdk 1.0.0, this repo as a package
uv run python experiments/example1.py                 # smoke test: real time, opens the SDK viewer
CL_SDK_ACCELERATED_TIME=1 uv run python fresh_eyes/run.py   # batch runs, faster than real time, no viewer
```

- **Always run from the repo root.** `cl` loads `.env` from there, and that selects the LIF simulator.
- `.env` is committed and the repo is public. **Never put secrets in it.**
- Only use numpy and scipy (scipy comes with `cl-sdk`). Ask before adding a dependency; one person runs
  `uv add`, so `pyproject.toml` and `uv.lock` don't conflict.

## Who owns which file

Each role owns its own files, so parallel work never conflicts. **Only edit files your role owns.** If you need a
change elsewhere, tell the human, who asks the owner.

| Role | Files |
|---|---|
| 1. Sim | `src/organoid_simulator/lif_data_source.py` (the adaptation change), `fresh_eyes/repeat_test.py` |
| 2. Images and colour | `fresh_eyes/images.py`, `fresh_eyes/encode.py` |
| 3. Silicon | `fresh_eyes/edges.py`, `fresh_eyes/alarm.py` |
| 4. Dish runner | `fresh_eyes/run.py`, `fresh_eyes/dish.py` (shared stim helpers and loop timing) |
| 5. Pitch and charts | `fresh_eyes/charts.py` |

Every file starts as a working stub, so the whole pipeline runs from the start. Each stub's docstring says what to
replace. Keep the signatures; swap in the real logic.

```bash
CL_SDK_ACCELERATED_TIME=1 uv run python fresh_eyes/repeat_test.py --adaptation-mv 1.0   # role 1's pass/fail test
CL_SDK_ACCELERATED_TIME=1 uv run python fresh_eyes/run.py --foods banana,strawberry     # full run -> runs/<ts>/
uv run python fresh_eyes/charts.py runs/<ts>                                            # summary.png + table
uv run python fresh_eyes/charts.py --fake runs/fake                                     # charts on fake data
```

`--adaptation-mv` and `--adaptation-tau-ms` fail until role 1's simulator change accepts them; leave them off until
then.

Shared files (`fresh-eyes-spec.md`, `AGENTS.md`, `pyproject.toml`): change them only when the human asks.

## The contract

Don't change these signatures without the whole team agreeing. They are what makes integration work.

```python
# fresh_eyes/images.py
make_stream(food: str, n_fresh: int, n_spoil: int) -> list[tuple[np.ndarray, float, bool]]  # (image, t, is_spoiled)
fruit_mask(image: np.ndarray) -> np.ndarray          # bool (64, 64); True on fruit pixels

# fresh_eyes/encode.py
encode(image: np.ndarray) -> dict[int, int]          # electrode -> pulse count; values ALWAYS sum to 12

# fresh_eyes/edges.py
edge_score(image: np.ndarray) -> float

# fresh_eyes/alarm.py
calibrate(scores: list[float]) -> tuple[float, float]               # (mean, std) of fresh scores
silicon_alarm(score: float, mean: float, std: float) -> bool        # score > mean + 3 * std
dish_alarm(response: int, baseline: float, margin: float) -> bool   # response > baseline * margin
```

Images are `uint8` arrays of shape `(64, 64, 3)` on a `(245, 245, 245)` background. Foods: `"banana"`,
`"strawberry"`.

`run.py` writes `runs/<timestamp>/<food>.csv`, one per food, with exactly these columns:

```
frame, t, is_spoiled, pulses_total, response_size, response_in, response_out, edge_score, dish_alarm, silicon_alarm
```

It also writes `runs/<timestamp>/meta.json`: the arguments, the simulator config, and per food the dish `baseline`,
`margin`, `edge_mean`, `edge_std` and every `calibration_responses` value (for recalibration time). Both alarms are
logged on every row, so dish only, silicon only and hybrid (either alarm) all come from one run. `runs/` is
gitignored.

## Rules that protect the science

- **Fixed pulse budget.** Colour chooses *which* electrodes get pulses, never *how many* in total. Every image gets
  exactly 12 pulses, and `pulses_total` is logged on every row to prove it. Don't change the encoder to intensity
  coding (more pulses for more brown); that turns "change detection" into "stronger stimulation" and invalidates
  the rebound control.
- **Electrode groups** (from the spec): yellow 9, 10 · green 13, 14 · brown 25, 26 · dark 29, 30 · red 49, 50 ·
  grey 53, 54.
- **Never stimulate the reserved channels** 0, 4, 7, 56, 63. They don't spike in the simulator and are
  ground/reference on a CL1.
- **Hardware limits:** at most 3 µA, 3 nC per phase, and 200 Hz per channel. Deliver multiple pulses on one electrode
  as a train with `cl.BurstDesign(n, 100)`, never as repeated `neurons.stim` calls in the same tick (pulses at the
  same timestamp merge into one).
- **Freeze the simulator config** (`adaptation_mV`, `adaptation_tau_ms`, `coupling_gain_mV`) and the alarm margin
  after the repeat test, before the scored runs. Never tune on scored runs.
- **Simulator results are not evidence about real neurons.** Label every chart and slide "simulated culture".
- `is_spoiled` is ground truth for scoring only. Nothing may train or tune on it.

## `cl` SDK cheat sheet

```python
import cl

if cl.is_simulator():                                    # raises RuntimeError on a CL1, so always guard it
    cl.sim.set_simulator_data_source(
        "organoid_simulator.lif_data_source:make_lif_source",
        config={"random_seed": 42, "coupling_gain_mV": 2.0, "adaptation_mV": 1.0},
    )

STIM = cl.StimDesign(200, -1.5, 200, 1.5)                # biphasic, cathodic first: (µs, µA) pairs

with cl.open() as neurons:
    for tick in neurons.loop(ticks_per_second=20, stop_after_seconds=60):
        for spike in tick.analysis.spikes:               # spikes since the previous tick
            spike.channel, spike.timestamp
        neurons.stim(cl.ChannelSet(9), STIM, cl.BurstDesign(3, 100))   # 3 pulses, 10 ms apart
```

- Data: 64 channels at 25 kHz. Channel number = `row * 8 + col` on the 8x8 grid.
- `tick.iteration` counts ticks from 0. Spikes reported on a tick happened during the interval before it.
- The simulator builds the data source in a separate process, so experiment code can't call methods on it
  directly. All configuration goes through the `config` dict.

## Git

- Work on your own branch (`<name>/<role>`), make small commits, and merge into `main` as soon as something runs.
- Don't rewrite history on `main`, and don't force-push.
- `origin` is the team fork (`YoosoofsahA/biocompute-outlier-labs`); `upstream` is the organisers' repo
  (`wbmills/biocompute-outlier-labs`). Never push to `upstream`.
