# Fresh Eyes results

Owner: role 4 (Dish runner). All runs are simulated (cl SDK simulator, LIF culture with adaptation). Run every
command from the repo root.

## Frozen settings

| Setting | Value | Where it came from |
|---|---|---|
| `coupling_gain_mV` | 1.0 | role 1's repeat test |
| `adaptation_mV` | 4.0 | role 1's repeat test |
| `adaptation_tau_ms` | 2000 (simulator default) | spec |
| Dish alarm signal | `response_in` (12 input electrodes) | whole-dish counts are swamped by spontaneous firing |
| Dish alarm margin | 1.5 | fresh-only runs, below |

**Margin check** (60 fresh banana frames after calibration, stub encoder): baseline `response_in` was 5.0 to 6.1
spikes. False alarms at 1.5x: 1, 0 and 1 out of 60 on seeds 1, 2 and 42. At 1.8x: none. 1.5 keeps false alarms
around 1% while leaving room for the roughly 2x novelty response measured in the repeat test.

## Scored runs

Run these only after roles 2 and 3 have merged their real images, encoder and edge detector. Don't change any
setting between runs.

| # | Experiment | Command | Run folder | Notes |
|---|---|---|---|---|
| 1 | Disconnect test + food switch + rebound | `CL_SDK_ACCELERATED_TIME=1 uv run python fresh_eyes/run.py --foods banana,strawberry` | | |
| 2 | Control: no adaptation | `CL_SDK_ACCELERATED_TIME=1 uv run python fresh_eyes/run.py --foods banana,strawberry --adaptation-mv 0` | | |
| 3 | Control: no reference refresh | `CL_SDK_ACCELERATED_TIME=1 uv run python fresh_eyes/run.py --foods banana --no-refresh` | | |
| 4 | Real-time run for the screen recording | `uv run python fresh_eyes/run.py --foods banana` | | |

### Results (3 Nov 2026, seed 42, simulated culture)

Protocol change before the scored runs: one test frame every 2 s with the fresh reference shown 3 times in between
(oddball design). At 0.5 s per check the culture got used to gradual browning frame by frame and the dish never fired.

| Run | Folder | Dish lead (checks) | Dish false alarms | Silicon lead | Hybrid lead |
|---|---|---|---|---|---|
| 1, main | `runs/run1/20261103-212853` | banana 12, strawberry 11 | banana 4/40, strawberry 0/40 | 26, 26 | 12, 11 |
| 2, adaptation off | `runs/run2/20261103-212851` | never, never | 0, 0 | 26, 26 | 26, 26 |
| 3, no refresh | `runs/run3/20261103-212741` | banana 12 | 1/40 | 26 | 12 |

Lead time is counted in checks from browning onset (t = 0.3); 60 spoilage checks span t = 0.3 to 1.0, so 12 checks is
t of about 0.44 and 26 is about 0.61, just after mould appears. The dish catches browning about 14 checks before
silicon; with adaptation off it never fires, so the effect comes from adaptation. Run 4 (real time) was not done.

After each run: `uv run python fresh_eyes/charts.py runs/<timestamp>`, then fill in the folder and a one-line note.
`runs/` is gitignored, so send the folders to role 5 directly.
