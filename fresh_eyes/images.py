"""Synthetic food images. Owner: role 2 (Images and colour).

STUB: plain squares of the food's colour that drift linearly to brown. Replace with a noisy blob, browning from
t = 0.3 and dark mould spots from t = 0.6, as in fresh-eyes-spec.md section 1.
"""
from __future__ import annotations

import numpy as np

SIZE = 64
BACKGROUND = (245, 245, 245)
FOODS = {"banana": (230, 200, 60), "strawberry": (200, 40, 50)}
BROWN = (110, 70, 30)
SPOIL_ONSET = 0.3
MOULD_ONSET = 0.6


def make_image(food: str, t: float) -> np.ndarray:
    """Return one (64, 64, 3) uint8 image of `food` at spoilage level `t` (0 fresh, 1 rotten)."""
    base = np.array(FOODS[food], dtype=float)
    drift = max(0.0, (t - SPOIL_ONSET) / (1 - SPOIL_ONSET))
    colour = (1 - drift) * base + drift * np.array(BROWN, dtype=float)
    image = np.full((SIZE, SIZE, 3), BACKGROUND, dtype=np.uint8)
    image[16:48, 16:48] = colour.round().astype(np.uint8)
    return image


def make_stream(food: str, n_fresh: int, n_spoil: int) -> list[tuple[np.ndarray, float, bool]]:
    """Return `n_fresh` frames at t = 0, then `n_spoil` frames with t ramping 0.3 to 1.0, as (image, t, is_spoiled)."""
    ts = [0.0] * n_fresh + list(np.linspace(SPOIL_ONSET, 1.0, n_spoil))
    return [(make_image(food, t), float(t), t >= SPOIL_ONSET) for t in ts]


def fruit_mask(image: np.ndarray) -> np.ndarray:
    """Return a bool (64, 64) mask that is True wherever the pixel differs from the background."""
    return np.any(np.abs(image.astype(int) - np.array(BACKGROUND)) > 10, axis=2)
