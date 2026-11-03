"""Repeat-the-same-stimulus test for the adaptation change. Owner: role 1 (Sim).

Shows pattern A 20 times, then pattern B once, then A once. Pass when A's response drops clearly over the repeats
and B comes back near A's first response. Without adaptation (the stock simulator) the A responses stay flat.

    CL_SDK_ACCELERATED_TIME=1 uv run python fresh_eyes/repeat_test.py
    CL_SDK_ACCELERATED_TIME=1 uv run python fresh_eyes/repeat_test.py --adaptation-mv 1.0
"""
from __future__ import annotations

import argparse

import cl
import numpy as np

from dish import COUNT_TICKS, TICKS_PER_CHECK, TICKS_PER_SECOND, sim_config, stimulate, use_lif

PATTERN_A = {9: 6, 10: 6}    # yellow group: fresh banana
PATTERN_B = {49: 6, 50: 6}   # red group: fresh strawberry, same 12-pulse budget


def main() -> None:
    """Run the test and print each response with a pass/fail verdict."""
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--repeats", type=int, default=20)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--coupling-mv", type=float, default=2.0)
    p.add_argument("--adaptation-mv", type=float)
    p.add_argument("--adaptation-tau-ms", type=float)
    args = p.parse_args()

    config = sim_config(args.seed, args.coupling_mv, args.adaptation_mv, args.adaptation_tau_ms)
    use_lif(config)
    schedule = [("A", PATTERN_A)] * args.repeats + [("B", PATTERN_B), ("A", PATTERN_A)]
    responses = [0] * len(schedule)

    with cl.open() as neurons:
        for tick in neurons.loop(ticks_per_second=TICKS_PER_SECOND, stop_after_ticks=len(schedule) * TICKS_PER_CHECK):
            k, phase = divmod(tick.iteration, TICKS_PER_CHECK)
            if phase in COUNT_TICKS:
                responses[k] += len(tick.analysis.spikes)
            if phase == 0:
                stimulate(neurons, schedule[k][1])

    print(f"config: {config}")
    for i, ((label, _), r) in enumerate(zip(schedule, responses)):
        print(f"  {i:2d} {label} {r:4d} {'#' * min(r, 60)}")
    first_a = np.mean(responses[:3])
    last_a = np.mean(responses[args.repeats - 5:args.repeats])
    b = responses[args.repeats]
    drop = last_a / first_a if first_a else float("nan")
    rebound = b / first_a if first_a else float("nan")
    print(f"\nA last5/first3 = {drop:.2f} (want well below 1)   B/first A = {rebound:.2f} (want near 1)")
    print("PASS" if drop < 0.7 and rebound > 0.8 else "FAIL: see the tuning order in fresh-eyes-spec.md section 4")


if __name__ == "__main__":
    main()
