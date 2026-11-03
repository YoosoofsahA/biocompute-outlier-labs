"""Dish runner. Owner: role 4 (Dish runner).

For each food: calibrate both halves on fresh frames, then play a stream (fresh, then spoiling), stimulating each
frame's colour pattern and counting the dish's response. Foods run back to back in one session, so
`--foods banana,strawberry` is the food-switch experiment.

Both alarms are logged on every row, so dish only, silicon only and hybrid (either alarm) all come from one run.

    CL_SDK_ACCELERATED_TIME=1 uv run python fresh_eyes/run.py
    CL_SDK_ACCELERATED_TIME=1 uv run python fresh_eyes/run.py --adaptation-mv 1.0 --foods banana,strawberry

Writes runs/<timestamp>/<food>.csv (the agreed columns) and runs/<timestamp>/meta.json.
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import cl
import numpy as np

from alarm import calibrate, dish_alarm, silicon_alarm
from dish import COUNT_TICKS, REFERENCE_TICKS, TICKS_PER_CHECK, TICKS_PER_SECOND, sim_config, stimulate, use_lif
from edges import edge_score
from encode import INPUT_ELECTRODES, PULSE_BUDGET, encode
from images import make_stream

COLUMNS = ["frame", "t", "is_spoiled", "pulses_total", "response_size", "response_in", "response_out",
           "edge_score", "dish_alarm", "silicon_alarm"]
BASELINE_CHECKS = 10


@dataclass
class Check:
    """One stimulus presentation and the response it got."""
    food: str
    live: bool
    frame: int
    image: np.ndarray
    t: float
    is_spoiled: bool
    pattern: dict[int, int] = field(default_factory=dict)
    edge: float = 0.0
    response_in: int = 0
    response_out: int = 0


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--foods", default="banana", help="comma-separated; later foods test recalibration")
    p.add_argument("--n-cal", type=int, default=30, help="fresh calibration checks per food")
    p.add_argument("--n-fresh", type=int, default=40)
    p.add_argument("--n-spoil", type=int, default=60)
    p.add_argument("--margin", type=float, default=1.5, help="dish alarm when response > baseline * margin")
    p.add_argument("--no-refresh", action="store_true", help="control: don't re-show the fresh reference")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--coupling-mv", type=float, default=1.0, help="frozen by role 1's repeat test")
    p.add_argument("--adaptation-mv", type=float, default=4.0, help="frozen by role 1; 0 is the no-adaptation control")
    p.add_argument("--adaptation-tau-ms", type=float, help="simulator default 2000")
    p.add_argument("--out", default="runs")
    return p.parse_args()


def build_checks(foods: list[str], n_cal: int, n_fresh: int, n_spoil: int) -> list[Check]:
    """Calibration checks then live checks, for each food in turn."""
    checks = []
    for food in foods:
        for i, (image, t, spoiled) in enumerate(make_stream(food, n_cal, 0)):
            checks.append(Check(food, False, i, image, t, spoiled))
        for i, (image, t, spoiled) in enumerate(make_stream(food, n_fresh, n_spoil)):
            checks.append(Check(food, True, i, image, t, spoiled))
    for check in checks:
        check.pattern = encode(check.image)
        check.edge = edge_score(check.image)
        if sum(check.pattern.values()) != PULSE_BUDGET:
            raise ValueError(f"encode() gave {sum(check.pattern.values())} pulses, not {PULSE_BUDGET}")
    return checks


def run_dish(checks: list[Check], refresh: bool) -> None:
    """Present every check to the dish and fill in its response counts."""
    references = {c.food: c.pattern for c in checks if not c.live and c.frame == 0}
    with cl.open() as neurons:
        for tick in neurons.loop(ticks_per_second=TICKS_PER_SECOND, stop_after_ticks=len(checks) * TICKS_PER_CHECK):
            k, phase = divmod(tick.iteration, TICKS_PER_CHECK)
            check = checks[k]
            if phase in COUNT_TICKS:
                for spike in tick.analysis.spikes:
                    if spike.channel in INPUT_ELECTRODES:
                        check.response_in += 1
                    else:
                        check.response_out += 1
            if phase == 0:
                stimulate(neurons, check.pattern)
            elif phase in REFERENCE_TICKS and refresh:
                stimulate(neurons, references[check.food])


def write_food(run_dir: Path, food: str, checks: list[Check], margin: float) -> dict:
    """Score one food's checks, write its CSV and return its calibration summary."""
    cal = [c for c in checks if c.food == food and not c.live]
    live = [c for c in checks if c.food == food and c.live]
    # The dish alarm reads the input electrodes only: that's where stimulus-specific adaptation shows, while
    # whole-dish counts are dominated by spontaneous firing.
    cal_responses = [c.response_in for c in cal]
    baseline = float(np.mean(cal_responses[-BASELINE_CHECKS:]))
    edge_mean, edge_std = calibrate([c.edge for c in cal])
    with (run_dir / f"{food}.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        for c in live:
            writer.writerow([c.frame, f"{c.t:.3f}", int(c.is_spoiled), sum(c.pattern.values()),
                             c.response_in + c.response_out, c.response_in, c.response_out, f"{c.edge:.3f}",
                             int(dish_alarm(c.response_in, baseline, margin)),
                             int(silicon_alarm(c.edge, edge_mean, edge_std))])
    return {"baseline": baseline, "baseline_signal": "response_in", "margin": margin, "edge_mean": edge_mean,
            "edge_std": edge_std, "calibration_responses": cal_responses,
            "calibration_responses_total": [c.response_in + c.response_out for c in cal]}


def main() -> None:
    """Run the experiment and write the CSVs."""
    args = parse_args()
    foods = args.foods.split(",")
    config = sim_config(args.seed, args.coupling_mv, args.adaptation_mv, args.adaptation_tau_ms)
    use_lif(config)

    checks = build_checks(foods, args.n_cal, args.n_fresh, args.n_spoil)
    print(f"{len(checks)} checks, {len(checks) * TICKS_PER_CHECK / TICKS_PER_SECOND:.0f} s of dish time ...")
    run_dish(checks, refresh=not args.no_refresh)

    run_dir = Path(args.out) / time.strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True)
    meta = {"args": vars(args), "sim_config": config, "simulated": cl.is_simulator(),
            "foods": {food: write_food(run_dir, food, checks, args.margin) for food in foods}}
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"Wrote {run_dir}\n  uv run python fresh_eyes/charts.py {run_dir}")


if __name__ == "__main__":
    main()
