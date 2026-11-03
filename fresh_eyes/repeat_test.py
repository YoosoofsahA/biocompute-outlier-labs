"""Repeat-the-same-stimulus test for the adaptation change. Owner: role 1 (Sim).

Shows pattern A 20 times, then pattern B once, then A once. Pass when A's whole-dish response drops clearly over
the repeats and, on the stimulated electrodes, B clears the adapted A response by NOVELTY_MIN. Without adaptation
the responses stay flat and B / adapted A is about 1.

The novelty is judged on the stimulated electrodes because that's where stimulus-specific adaptation lives.
Spontaneous firing on every other channel adapts too (the whole culture quietens) and adds noise, so the
whole-dish B / adapted A ratio varies a lot between seeds. It's printed for reference.

    CL_SDK_ACCELERATED_TIME=1 uv run python fresh_eyes/repeat_test.py
    CL_SDK_ACCELERATED_TIME=1 uv run python fresh_eyes/repeat_test.py --adaptation-mv 1.0
"""
from __future__ import annotations

import argparse

import cl
import numpy as np

from dish import COUNT_TICKS, TICKS_PER_SECOND, sim_config, stimulate, use_lif

PATTERN_A = {9: 6, 10: 6}    # yellow group: fresh banana
PATTERN_B = {49: 6, 50: 6}   # red group: fresh strawberry, same 12-pulse budget
TICKS_PER_CHECK = 10         # 0.5 s per presentation; this test predates the 2 s oddball schedule
NOVELTY_MIN = 1.5            # B must clear the adapted baseline by the dish alarm's margin


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
    on_target = [0] * len(schedule)              # spikes on the electrodes just stimulated

    with cl.open() as neurons:
        for tick in neurons.loop(ticks_per_second=TICKS_PER_SECOND, stop_after_ticks=len(schedule) * TICKS_PER_CHECK):
            k, phase = divmod(tick.iteration, TICKS_PER_CHECK)
            if phase in COUNT_TICKS:
                responses[k] += len(tick.analysis.spikes)
                on_target[k] += sum(s.channel in schedule[k][1] for s in tick.analysis.spikes)
            if phase == 0:
                stimulate(neurons, schedule[k][1])

    print(f"config: {config}")
    print("   # pattern  total  on stimulated electrodes")
    for i, ((label, _), r, t) in enumerate(zip(schedule, responses, on_target)):
        print(f"  {i:2d} {label}       {r:4d}  {t:4d}  {'#' * min(r, 50)}")
    first_a = responses[0]                       # the only unadapted A response
    last_a = float(np.mean(responses[args.repeats - 5:args.repeats]))
    last_a_on = float(np.mean(on_target[args.repeats - 5:args.repeats]))
    b = responses[args.repeats]
    drop = last_a / first_a if first_a else float("nan")
    novelty_on = on_target[args.repeats] / last_a_on if last_a_on else float("nan")
    print(f"\nA drop, whole dish: last5/first = {drop:.2f} (want < 0.7)")
    print(f"Novelty, stimulated electrodes: B / adapted A = {novelty_on:.2f} (want >= {NOVELTY_MIN})")
    print(f"For reference, whole dish: B / adapted A = {b / last_a if last_a else float('nan'):.2f}, "
          f"B / first A = {b / first_a if first_a else float('nan'):.2f}")
    passed = drop < 0.7 and novelty_on >= NOVELTY_MIN
    print("PASS" if passed else "FAIL: see the tuning order in fresh-eyes-spec.md section 4")


if __name__ == "__main__":
    main()
