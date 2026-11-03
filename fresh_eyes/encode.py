"""Colour to stimulation. Owner: role 2 (Images and colour).

Colour picks WHICH electrodes get pulses; every image gets exactly PULSE_BUDGET pulses in total.

STUB: all pulses go to the yellow group. Replace with the six HSV bins from fresh-eyes-spec.md section 3, splitting
the budget by each bin's share of fruit pixels (largest-remainder rounding).
"""
from __future__ import annotations

import numpy as np

PULSE_BUDGET = 12
GROUPS = {
    "yellow": (9, 10),
    "green": (13, 14),
    "brown": (25, 26),
    "dark": (29, 30),
    "red": (49, 50),
    "grey": (53, 54),
}
INPUT_ELECTRODES = frozenset(ch for group in GROUPS.values() for ch in group)


def encode(image: np.ndarray) -> dict[int, int]:
    """Return electrode -> pulse count for `image`. The counts always sum to PULSE_BUDGET."""
    a, b = GROUPS["yellow"]
    return {a: PULSE_BUDGET // 2, b: PULSE_BUDGET - PULSE_BUDGET // 2}
