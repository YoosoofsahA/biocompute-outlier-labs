# Fresh Eyes: hybrid spoilage detector, team spec

Nov 3, 2026 · @Ismail · revision 2

## What changed in this revision

1. **Encoder:** colour now picks *which* electrodes fire, and every image gets the same total number of pulses. In
   revision 1, colour set the pulse *count* on the same 4 electrodes, so "change" just meant "more or less
   stimulation". That made the dish result and the rebound control meaningless. Mean hue and the red-to-green ratio
   also pointed in opposite directions.
2. **No mean hue.** Hue wraps at 0/360, so a noisy strawberry averaged to cyan. We use colour bins instead.
3. **Pulses are spaced** with `cl.BurstDesign` so each one can fire the neuron. Pulses at the same timestamp merge
   into one bigger pulse.
4. **Coupling starts lower** (2.0, not 4.0). Shared downstream neurons adapt to everything and dull the rebound.
5. **`is_spoiled = t >= 0.3`** (was `>`), and fresh frames have `t = 0`.
6. **Pitch wording:** "simulated culture", "gets used to" (not "learns"), no energy claim. Cites real-culture
   precedent for selective adaptation.
7. **Roles rebalanced:** the images owner also writes the encoder's colour bins (pure numpy), so the dish runner only
   owns the loop.

## The project

A spoilage detector that needs zero labelled photos of rotten food. Silicon finds shapes (edges, mould spots). A
simulated dish of neurons gets used to what fresh colour looks like and responds strongly when the colour changes.
We then unplug each half to show what each catches, switch food type to show it recalibrates with no labels, and
compare a compiled electrode layout against a random one.

**Pitch line:** "Spoilage detectors need thousands of labelled photos of rotten food for every product. Ours needs
none: a culture of neurons gets used to what fresh looks like and reacts to anything that isn't. Silicon handles the
shapes, neurons handle the change."

Built on the organisers' simulator (`wbmills/biocompute-outlier-labs`) and the Cortical Labs `cl` SDK, so the dish
half runs unchanged on a CL1. **Everything tonight runs on the simulator. Say so on every results slide.**

## Pipeline and implementation

Five pieces in a chain: synthetic images, a silicon edge detector, a colour encoder that stimulates the dish, a
habituation change in the simulator, and an alarm that combines both.

### 1. Images (`images.py`, numpy only)

- 64x64 RGB arrays on a plain background, `(245, 245, 245)`. A "food" is a blob of base colour plus noise: banana
  `(230, 200, 60)`, strawberry `(200, 40, 50)`.
- Spoilage over time `t` from 0 to 1: colour drifts toward brown `(110, 70, 30)` from `t = 0.3` (early, invisible to
  edges); dark mould spots appear from `t = 0.6` (visible to edges).
- `make_stream(food, n_fresh, n_spoil)` returns a list of `(image, t, is_spoiled)`. Fresh frames have `t = 0`;
  spoilage frames ramp `t` from 0.3 to 1.0. `is_spoiled = t >= 0.3`. Ground truth is for scoring only; nothing is
  trained on it.
- `fruit_mask(image) -> bool array`: pixels that differ from the background. Both halves use it.

### 2. Silicon half (`edges.py`)

- Sobel filter on greyscale (numpy, or `scipy.ndimage.sobel`), count pixels inside the fruit mask above a threshold,
  output `edge_score` per frame.
- Calibrate on fresh frames: mean and standard deviation of `edge_score`. Alarm if a frame is more than 3 standard
  deviations above the fresh mean.

### 3. Dish half: encoder (`encode.py`)

**Colour picks the electrodes; the pulse budget is fixed.**

1. Convert fruit-mask pixels to HSV and put each pixel in one of six bins, checked in this order:

   | Bin | Rule | Catches |
   |---|---|---|
   | dark | V < 0.25 | mould spots, black rot |
   | grey | S < 0.25 | white or grey mould |
   | red | H < 15° or H >= 330° | strawberry |
   | brown | 15° <= H < 40° | browning (brown is H about 30°, V about 0.43) |
   | yellow | 40° <= H < 70° | banana (H about 49°, V about 0.9) |
   | green | 70° <= H < 170° | unripe, green mould |

   Pixels outside these hues are ignored.

2. Each bin owns two input electrodes, spread across the array and away from the reserved channels (0, 4, 7, 56, 63):

   | Bin | Electrodes |
   |---|---|
   | yellow | 9, 10 |
   | green | 13, 14 |
   | brown | 25, 26 |
   | dark | 29, 30 |
   | red | 49, 50 |
   | grey | 53, 54 |

3. **Fixed budget:** 12 pulses per check, split across bins in proportion to each bin's share of fruit pixels
   (largest-remainder rounding, so the total is always exactly 12), then split evenly across the bin's two
   electrodes.
4. Deliver each electrode's pulses as one train: `cl.StimDesign(200, -1.5, 200, 1.5)` with
   `cl.BurstDesign(n, 100)`. At 100 Hz the pulses are 10 ms apart, so each can fire the neuron (2 ms refractory),
   and we stay under the SDK's 200 Hz per-channel limit.

`encode(image) -> dict[int, int]` maps electrode to pulse count. Its values always sum to 12. Fresh banana puts most
pulses on 9 and 10; as it browns, pulses move to 25 and 26. The total drive never changes, so a bigger response can
only come from neurons that haven't adapted yet.

**Response:** spikes in the 100 ms after stimulation (ticks 1 and 2). Log three numbers:

- `response_size`: all spiking channels (the alarm uses this)
- `response_in`: the 12 input electrodes only
- `response_out`: everything else

The split shows where adaptation is happening. On a real CL1, ignore stimulated channels for the first 5 ms after
each pulse (stimulation artifact); the simulator doesn't model the artifact.

### 4. Simulator change: habituation (Sim owner, about 10 lines)

The LIF model has no adaptation, so repeated stimulation never gets a smaller response. Add spike-frequency
adaptation, which real neurons have, in `src/organoid_simulator/lif_data_source.py`:

1. `__init__`: new params `adaptation_mV: float = 0.0` (off by default) and `adaptation_tau_ms: float = 2000.0`.
   Store the per-frame decay `exp(-MS_PER_FRAME / adaptation_tau_ms)`.
2. `open()`: allocate `self._theta = np.zeros(n)`, with `n` the number of model neurons (64, or `n_units` in spatial
   mode), next to the other per-neuron state.
3. `read()`, per frame, before the threshold check: `theta *= decay` (use a local, like `V`).
4. Change both threshold checks (the two `fired = (V >= self._v_thresh) ...` lines) to `V >= self._v_thresh + theta`.
5. After `fired` is computed: `theta[fired] += self._adaptation_mV`. Write it back to `self._theta` at the end, as
   `V` is.
6. Run with config `{"random_seed": 42, "coupling_gain_mV": 2.0, "adaptation_mV": 1.0}`.

**Repeat-the-same-stimulus test (do this before anything else):** show the fresh-banana pattern 20 times, then the
fresh-strawberry pattern once. Pass if the banana response drops clearly over the 20 repeats *and* the strawberry
response comes back near the first banana response. Tune in this order:

- Response doesn't drop: raise `adaptation_mV` (0.5 to 3).
- Drops, but strawberry doesn't rebound: lower `coupling_gain_mV` (shared downstream neurons are adapting to
  everything), then lengthen `adaptation_tau_ms`.

Freeze the config once it passes. Don't tune on the scored runs.

### 5. Alarm (`alarm.py`)

- **Calibration:** show fresh frames for 20 to 40 checks (10 to 20 s of sim time). The baseline is the mean
  `response_size` of the last 10.
- **Live:** alarm if `response_size` exceeds the baseline by a margin fixed after the repeat test and before the
  scored runs (start at 1.5x), or if the silicon alarm fires.
- **Reference refresh:** between live checks, re-show the stored fresh reference image, so the dish stays used to
  fresh rather than slowly getting used to spoiling food.

### Loop shape

`neurons.loop(ticks_per_second=20)`. One check every 10 ticks (0.5 s):

| Tick | Action |
|---|---|
| 0 | stimulate the frame's pattern |
| 1–2 | count spikes (the response) |
| 5 | stimulate the fresh reference (not counted) |
| other | idle |

Use `CL_SDK_ACCELERATED_TIME=1` for batch runs, and real time with the viewer for the demo recording.

## Experiments and the numbers

One stream per run: 40 fresh frames, then 60 spoilage frames with `t` from 0.3 to 1.0. Score each frame against
`is_spoiled`.

| Experiment | Conditions | What it shows |
|---|---|---|
| Disconnect test (headline) | Hybrid; dish only (silicon off); silicon only (dish off) | What each half catches. Expect the dish to catch early colour drift (t 0.3 to 0.6) and silicon to catch mould spots (t above 0.6). |
| Food switch (flexibility) | Banana stream, then 20 checks of fresh strawberry, then a strawberry spoilage stream | Recalibrates with zero labels. With a 2 s adaptation memory, expect it to recalibrate within a few checks. |
| Layout compiler (if time) | Electrode pairs chosen from a 1-minute stim-response map vs random pairs | Pick pairs that drive the *least overlapping* sets of other channels, so adapting to one colour doesn't dull another. Expect a bigger rebound and an earlier alarm. |

**Controls, all required for the science slide:**

- **Rebound:** after getting used to fresh banana, show fresh strawberry. The response must jump back up. With the
  fixed pulse budget this proves it detects change, not that the neurons are just tired.
- **No adaptation:** `adaptation_mV: 0`. The response stays flat whatever the colour, because total drive never
  changes, so the dish alarm can't separate fresh from spoiled.
- **No reference refresh:** run once without re-showing the fresh image, and show whether slow browning gets
  habituated away.

**Be upfront about the data:** the images are built so the colour drift starts before the spots. The disconnect
test shows the hybrid routes each signal to the half that can see it; it doesn't discover that split.

**Numbers on the slide, per condition:**

- **Detection lead time:** frames from spoilage onset (t = 0.3) to first alarm. Earlier is better.
- **False alarms:** alarms on fresh frames.
- **Recalibration time:** fresh frames needed after the food switch before the alarm is usable.

**Charts:**

1. `response_size` over frames, with spoilage onset and mould onset marked and the alarm threshold as a line. The
   dish's story at a glance.
2. One table: lead time and false alarms for hybrid, dish only, silicon only.

## Five roles and timeline

All five start at once against agreed function signatures. Roles 1 and 4 are the critical path, so they start
first.

| Role | Owns | Interface | Done by |
|---|---|---|---|
| 1. Sim | `uv sync` on all laptops; the adaptation change; the repeat-the-same-stimulus test and tuning | Frozen config dict for `set_simulator_data_source` | 20:55 |
| 2. Images and colour | `make_stream`, `fruit_mask`; banana and strawberry; brown drift then mould spots; `encode(image)` colour bins and fixed budget | `make_stream(...) -> list[(image, t, is_spoiled)]`; `encode(image) -> dict[electrode, pulses]` summing to 12 | 20:55 |
| 3. Silicon | `edges.py`: Sobel `edge_score(image)`; `alarm.py`: `calibrate`, `silicon_alarm`, `dish_alarm` | `edge_score(image) -> float`; alarm signatures in `AGENTS.md` | 20:50 |
| 4. Dish runner | `run.py`: the loop that stims and counts responses; calibration, reference refresh, calling `dish_alarm`; the three disconnect runs and the food switch; a CSV per run | CSV columns: `frame, t, is_spoiled, pulses_total, response_size, response_in, response_out, edge_score, dish_alarm, silicon_alarm` | 21:10 |
| 5. Pitch and charts | Slides; chart script from the CSV (test on a fake CSV now); screen recording of the viewer during calibration and spoilage | Reads the CSVs | 21:25 |

Role 3 finishes first and helps role 4 with runs and controls. `pulses_total` must be 12 on every row; it's the
proof that drive never changed.

**Timeline:**

- 20:45 to 20:55: parallel build. Role 1 runs the repeat test as soon as the change compiles.
- 20:55 to 21:05: integrate; one real-time run with the viewer to check responses shrink during calibration.
- 21:05 to 21:15: accelerated runs: hybrid, dish only, silicon only, food switch, then the controls.
- 21:15 to 21:30: charts into slides, rehearse.

**Cut lines:**

- **Habituation not visible by 21:00:** raise `adaptation_mV`, lengthen `adaptation_tau_ms`, lower coupling. Still
  flat: present silicon only plus the dish pipeline, and pitch habituation as the CL1-day test (real cultures show
  selective adaptation).
- **Short on time:** drop the layout compiler and the no-refresh control first, then the food switch. Never drop the
  disconnect test or the rebound control.

## Pitch outline

Five slides, under four minutes, no em dashes.

1. **Problem:** about a third of food is wasted. Camera-based spoilage detection needs thousands of labelled photos
   of rotten food, per product, and fails when the product changes.
2. **Idea:** split the job. Silicon finds shapes (mould, bruises). Neurons do what they are naturally good at:
   getting used to the normal and reacting to change. No labels needed.
3. **What we built:** synthetic food images, an edge detector, a colour-to-stimulation encoder on the `cl` SDK, and
   the organisers' simulator with one honest addition (neuron adaptation, which real neurons have).
4. **Results (simulated culture):** the response chart (shrinks on fresh, jumps on spoilage). The disconnect table:
   the dish catches early colour drift, silicon catches mould, together they catch both. The rebound control
   proves it's change detection, not fatigue. The food switch: recalibrated with no labels.
5. **The ask:** the dish half runs unchanged on a CL1. One day: habituation, spoilage stream, rebound control and
   the food switch on real neurons.

**Likely questions:**

- **"Couldn't a simple algorithm do change detection?"** Yes, and we say so. The claim is that neurons do it
  natively, with no training, and the CL1 day measures how well.
- **"Isn't the habituation something you added?"** Yes, to the simulator, because the stock model has none. Real
  cultures adapt selectively: responses to a frequent stimulus shrink while a rare one still gets a full response
  (Eytan, Brenner & Marom, *Journal of Neuroscience*, 2003). The CL1 day tests the real thing.
- **"Isn't the stronger response just stronger stimulation?"** No. Every image gets exactly 12 pulses; colour only
  changes which electrodes get them. The CSV logs the total on every frame.
- **"Isn't the disconnect result built into your images?"** Yes, deliberately: we made a stream where each half has
  its own signal, and the test shows the hybrid catches both.
- **"Won't it adapt to slow spoilage too?"** Yes, which is why we re-show a fresh reference between checks, and we
  show the run without it.
- **"Why images and not a gas sensor?"** The same pipeline takes any sensor stream; images make the demo visible.
