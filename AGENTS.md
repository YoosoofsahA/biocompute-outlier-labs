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

## Role briefs

Find your role and follow its brief. Every brief has the same parts: the goal, the steps, how to check your work,
and what "done" means. When you're done, merge to `main` and tell the team.

### Role 1: Sim (adaptation change)

**Goal:** make repeated identical stimulation get a smaller response, while a different stimulus still gets a full
one. The stock simulator has no adaptation, so `repeat_test.py` currently FAILS (the banana response drops only
about 5%).

**Files:** `src/organoid_simulator/lif_data_source.py`, `fresh_eyes/repeat_test.py`.

**Steps:**

1. In `LIFDataSource.__init__`, add `adaptation_mV: float = 0.0` and `adaptation_tau_ms: float = 2000.0` to the
   signature and the docstring. Store `self._adaptation_mV` and the per-frame decay
   `self._theta_decay = float(np.exp(-MS_PER_FRAME / adaptation_tau_ms))`. `make_lif_source(**kwargs)` forwards to
   `__init__`, so nothing else is needed for the config dict to reach it.
2. Declare `self._theta: np.ndarray | None = None` next to `self._V` in `__init__`. In `open()`, allocate
   `self._theta = np.zeros(n)` next to `self._V = np.full(n, ...)`. In `close()`, reset it to `None` like `self._V`.
3. In `read()`, take a local `theta = self._theta` next to `V = self._V`. Inside the per-frame loop, before the
   threshold check, do `theta *= self._theta_decay`.
4. Change **both** threshold checks (the spatial and non-spatial `fired = (V >= self._v_thresh) ...` lines) to
   `V >= self._v_thresh + theta`.
5. Right after `fired` is computed: `theta[fired] += self._adaptation_mV`. `theta` is the same array as
   `self._theta`, so updating it in place persists across `read()` calls.
6. With `adaptation_mV = 0` the behaviour must be identical to before.

**Check:**

```bash
CL_SDK_ACCELERATED_TIME=1 uv run python fresh_eyes/repeat_test.py                     # still runs, FAIL (no adaptation)
CL_SDK_ACCELERATED_TIME=1 uv run python fresh_eyes/repeat_test.py --adaptation-mv 1.0 # aim for PASS
```

Tune in this order until PASS: raise `--adaptation-mv` (0.5 to 3); if A drops but B doesn't rebound, lower
`--coupling-mv`, then try a longer `--adaptation-tau-ms`. Don't touch the pass thresholds in `repeat_test.py` to
make it pass.

**Done:** `repeat_test.py` prints PASS. Post the frozen values (`coupling_mV`, `adaptation_mV`,
`adaptation_tau_ms`) to the team; role 4 makes them the defaults. Then help role 4 with runs.

### Role 2: Images and colour

**Goal:** realistic synthetic food frames, and an encoder that turns colour into *which* electrodes fire.

**Files:** `fresh_eyes/images.py`, `fresh_eyes/encode.py`.

**Steps for `images.py`:**

1. Draw the food as an ellipse (about 40x24 px) of its base colour on the `(245, 245, 245)` background, with
   per-pixel noise (standard deviation about 8 per channel). Seed the noise from the food and the frame index inside
   `make_stream`, e.g. `np.random.default_rng((list(FOODS).index(food), i))`, so runs are reproducible. Don't use
   `hash()`; it changes between Python processes.
2. **Browning:** from `t = 0.3`, blend the fruit pixels toward `BROWN` linearly, reaching full brown at `t = 1`.
   Browning must be even across the fruit, with no new edges; it's the dish's signal only.
3. **Mould:** from `t = 0.6`, add dark round spots (radius 2 to 4 px, colour about `(40, 35, 30)`, so HSV value is
   below 0.25), placed inside the fruit, growing from 1 spot at `t = 0.6` to about 8 at `t = 1`. Spots are
   silicon's main signal.
4. Keep `make_stream` and `fruit_mask` signatures exactly. `fruit_mask` must exclude the background and include the
   spots.

**Steps for `encode.py`:**

1. Convert fruit-mask pixels to HSV with `matplotlib.colors.rgb_to_hsv(image / 255)` (hue comes back 0 to 1;
   multiply by 360).
2. Bin each pixel by the rules in `fresh-eyes-spec.md` section 3, **checked in that order**: dark (V < 0.25), grey
   (S < 0.25), red, brown, yellow, green. Ignore pixels in no bin.
3. Split `PULSE_BUDGET` (12) across bins in proportion to their pixel share, using largest-remainder rounding so the
   total is exactly 12. Split each bin's pulses across its two electrodes (5 becomes 3 and 2).
4. If no pixel lands in any bin, give 1 pulse to each of the 12 input electrodes.
5. Don't change `GROUPS` or `PULSE_BUDGET`; they're in the spec and the runner depends on them.

**Check:** for both foods, every frame from `make_stream(food, 5, 20)` gives `sum(encode(img).values()) == 12`.
Fresh banana puts most pulses on 9 and 10; banana at `t = 1` puts most on 25, 26 (brown) and 29, 30 (dark); fresh
strawberry puts most on 49 and 50. Save a few frames as PNGs (`matplotlib.pyplot.imsave`) and look at them.

**Done:** those checks pass and the frames look like fruit. Tell role 3, whose edge detector depends on your spots.

### Role 3: Silicon (edge detector)

**Goal:** a score that stays low and steady on fresh fruit and browning fruit, and jumps when mould spots appear.

**Files:** `fresh_eyes/edges.py`, `fresh_eyes/alarm.py`.

**Steps:**

1. In `edge_score`: convert to greyscale (`image.mean(axis=2)` as float), compute
   `np.hypot(scipy.ndimage.sobel(grey, 0), scipy.ndimage.sobel(grey, 1))`.
2. **Erode the fruit mask** before counting (`scipy.ndimage.binary_erosion(fruit_mask(image), iterations=3)`).
   Otherwise the fruit's own outline counts as edges on every frame.
3. Return the number of pixels inside the eroded mask whose edge strength is above a threshold. Pick the threshold
   from the data: above the noise on fresh frames, below the edge of a mould spot.
4. In `alarm.py`, give `silicon_alarm` a floor on `std`: `max(std, 1.0)`. If every fresh frame scores the same,
   `std` is 0 and the slightest noise would trigger the alarm. Leave the signatures alone.

**Check:** on `make_stream("banana", 20, 60)`, scores for `t = 0` frames and `0.3 <= t < 0.6` frames are low and
similar (browning must NOT raise the score); scores for `t >= 0.6` are clearly higher and grow with `t`. Same for
strawberry.

**Done:** those checks pass. Then help role 4 with the runs.

### Role 4: Dish runner

**Goal:** produce the results: one run per experiment, using frozen settings, with the run folders recorded.

**Files:** `fresh_eyes/run.py`, `fresh_eyes/dish.py`, and `results.md` (create it).

`run.py` already works end to end. Your job is running the experiments correctly, not rewriting it.

**Steps:**

1. Pull `main` every 10 minutes and run a short smoke test (`--n-cal 10 --n-fresh 10 --n-spoil 10`) so breakage
   shows up early.
2. When role 1 posts the frozen values, set them as the defaults of `--coupling-mv`, `--adaptation-mv` and
   `--adaptation-tau-ms` in `run.py`.
3. Choose `--margin` from a fresh-only calibration run (set it so fresh frames don't alarm), then freeze it as the
   default **before** any scored run.
4. Run the experiments with `CL_SDK_ACCELERATED_TIME=1`, from the repo root:

   | Experiment | Command flags |
   |---|---|
   | Disconnect test + food switch + rebound (one run) | `--foods banana,strawberry` |
   | Control: no adaptation | `--foods banana,strawberry --adaptation-mv 0` |
   | Control: no reference refresh | `--foods banana --no-refresh` |

   One run covers the disconnect test because both alarms are logged on every row. The rebound is read from
   `meta.json`: the first strawberry calibration responses compared with the banana baseline.
5. Do one **real-time** run (no `CL_SDK_ACCELERATED_TIME`) with `--foods banana` so role 5 can screen-record the
   viewer.

**Check:** every CSV row has `pulses_total = 12`; `meta.json` has the frozen `sim_config`.

**Done:** `results.md` lists each run folder, its condition and the exact command, and the run folders are shared
with role 5 (`runs/` is gitignored, so send them directly or zip them).

### Role 5: Pitch and charts

**Goal:** the slides and the charts that make the result obvious in under four minutes.

**Files:** `fresh_eyes/charts.py`, the slides.

**Steps:**

1. Run `uv run python fresh_eyes/charts.py --fake runs/fake` now and build the slides around that output, so
   real results drop straight in.
2. Add to `charts.py`:
   - **Rebound:** from `meta.json`, plot the end of banana's calibration and live responses next to strawberry's
     first calibration responses.
   - **Recalibration time:** the number of strawberry calibration checks until the response stays under
     `baseline * margin`.
   - **Comparison:** a `--compare RUN_A RUN_B` option that overlays two runs' response charts (adaptation on vs
     off, refresh vs no refresh).
3. Slides: follow the pitch outline in `fresh-eyes-spec.md`. Five slides, under four minutes, no em dashes. Label
   every chart "simulated culture".
4. Screen-record the viewer during role 4's real-time run.

**Check:** the charts build from both the fake run and a real run without edits.

**Done:** slides contain the real charts and the disconnect table, and the team has rehearsed once.

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
