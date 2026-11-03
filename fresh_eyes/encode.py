"""Colour to stimulation. Owner: role 2 (Images and colour).

Colour picks WHICH electrodes get pulses; every image gets exactly PULSE_BUDGET pulses in total.

Fruit pixels go into six HSV bins (fresh-eyes-spec.md section 3, checked in order: dark, grey, red, brown, yellow,
green). The budget is split across bins by each bin's share of binned pixels with largest-remainder rounding, then
split evenly across the bin's two electrodes.
"""
from __future__ import annotations

import numpy as np
from matplotlib.colors import rgb_to_hsv

from images import fruit_mask

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
BIN_ORDER = ("dark", "grey", "red", "brown", "yellow", "green")


def bin_counts(image: np.ndarray) -> dict[str, int]:
    """Return the number of fruit pixels in each colour bin. Pixels outside every bin are not counted."""
    pixels = image[fruit_mask(image)]
    if len(pixels) == 0:
        return {name: 0 for name in BIN_ORDER}
    hsv = rgb_to_hsv(pixels / 255.0)
    h, s, v = hsv[:, 0] * 360.0, hsv[:, 1], hsv[:, 2]
    rules = {
        "dark": v < 0.25,
        "grey": s < 0.25,
        "red": (h < 15) | (h >= 330),
        "brown": (h >= 15) & (h < 40),
        "yellow": (h >= 40) & (h < 70),
        "green": (h >= 70) & (h < 170),
    }
    unclaimed = np.ones(h.shape, dtype=bool)
    counts = {}
    for name in BIN_ORDER:
        hit = rules[name] & unclaimed
        counts[name] = int(hit.sum())
        unclaimed &= ~hit
    return counts


def split_budget(counts: dict[str, int], budget: int = PULSE_BUDGET) -> dict[str, int]:
    """Split `budget` across bins in proportion to `counts` (largest remainder; ties go to the earlier bin).

    With no binned pixels at all, the budget is spread evenly over every bin (1 pulse per input electrode).
    """
    weights = np.array([counts.get(name, 0) for name in BIN_ORDER], dtype=float)
    if weights.sum() == 0:
        weights[:] = 1.0
    exact = budget * weights / weights.sum()
    pulses = np.floor(exact).astype(int)
    for i in sorted(range(len(BIN_ORDER)), key=lambda i: -(exact[i] - pulses[i]))[: budget - pulses.sum()]:
        pulses[i] += 1
    return {name: int(n) for name, n in zip(BIN_ORDER, pulses)}


def encode(image: np.ndarray) -> dict[int, int]:
    """Return electrode -> pulse count for `image`. The counts always sum to PULSE_BUDGET; zero counts are left out."""
    pattern = {}
    for name, n in split_budget(bin_counts(image)).items():
        a, b = GROUPS[name]
        for channel, count in ((a, n - n // 2), (b, n // 2)):
            if count:
                pattern[channel] = count
    return pattern
