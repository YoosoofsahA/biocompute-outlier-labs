"""Alarms for both halves. Owner: role 3 (Silicon).

Both alarms calibrate on fresh frames only, so neither needs labelled rotten food.
"""
from __future__ import annotations

import numpy as np

SILICON_SIGMA = 3.0


def calibrate(scores: list[float]) -> tuple[float, float]:
    """Return the (mean, std) of scores from fresh frames."""
    return float(np.mean(scores)), float(np.std(scores))


def silicon_alarm(score: float, mean: float, std: float) -> bool:
    """True if `score` is more than SILICON_SIGMA standard deviations above the fresh mean."""
    return score > mean + SILICON_SIGMA * std


def dish_alarm(response: int, baseline: float, margin: float) -> bool:
    """True if the dish's response exceeds its habituated fresh baseline by `margin` (e.g. 1.5x)."""
    return response > baseline * margin
