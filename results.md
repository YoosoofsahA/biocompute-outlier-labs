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

After each run: `uv run python fresh_eyes/charts.py runs/<timestamp>`, then fill in the folder and a one-line note.
`runs/` is gitignored, so send the folders to role 5 directly.
