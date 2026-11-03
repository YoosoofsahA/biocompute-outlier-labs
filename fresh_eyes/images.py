"""Synthetic food images. Owner: role 2 (Images and colour).

A food is an ellipse of base colour plus per-pixel noise on a plain background (fresh-eyes-spec.md section 1).
From t = 0.3 the whole ellipse drifts evenly toward brown, adding no edges inside the fruit. From t = 0.6 dark mould
spots appear one by one and grow, which the edge detector can see.

Browning is complete at BROWN_FULL = 0.6, not t = 1 as the AGENTS.md brief says. Blending in RGB, a pixel only moves
from the food's colour bin into the brown bin at about two thirds of the way to brown; finishing at t = 1 would put
that after mould onset (banana 11% brown at t = 0.6, strawberry 1%), so the dish would have no early signal.

Frames are deterministic: frame i of a food is seeded from (food index, i).
"""
from __future__ import annotations

import numpy as np

SIZE = 64
BACKGROUND = (245, 245, 245)
FOODS = {"banana": (230, 200, 60), "strawberry": (200, 40, 50)}
BROWN = (110, 70, 30)
MOULD = (40, 35, 30)
SPOIL_ONSET = 0.3
MOULD_ONSET = 0.6
BROWN_FULL = 0.6       # t at which the colour drift is complete; see the module docstring
NOISE_SD = 8.0         # per-pixel colour noise, in 0-255 units
HALF_AXES = (20, 12)   # ellipse half-width and half-height: a 40x24 px fruit
N_SPOTS = 8
SPOT_RADIUS = (2.0, 4.0)
SPOT_MARGIN = 4        # spot centres stay this many pixels inside the fruit's edge

_YY, _XX = np.mgrid[0:SIZE, 0:SIZE]
SHAPE = ((_XX - SIZE / 2 + 0.5) / HALF_AXES[0]) ** 2 + ((_YY - SIZE / 2 + 0.5) / HALF_AXES[1]) ** 2 <= 1


def _food_index(food: str) -> int:
    if food not in FOODS:
        raise ValueError(f"unknown food {food!r}; expected one of {sorted(FOODS)}")
    return list(FOODS).index(food)


def _spots(food: str) -> list[tuple[float, float, float]]:
    """Return (y, x, t_appear) for each mould spot: 1 spot at t = 0.6, all N_SPOTS by t = 0.95."""
    core = SHAPE.copy()
    for dy in range(-SPOT_MARGIN, SPOT_MARGIN + 1):
        for dx in range(-SPOT_MARGIN, SPOT_MARGIN + 1):
            core &= np.roll(SHAPE, (dy, dx), axis=(0, 1))
    core = np.argwhere(core)
    picks = core[np.random.default_rng((_food_index(food),)).choice(len(core), N_SPOTS, replace=False)]
    appear = np.linspace(MOULD_ONSET, 0.95, N_SPOTS)
    return [(float(y), float(x), float(ta)) for (y, x), ta in zip(picks, appear)]


def make_image(food: str, t: float, frame: int = 0) -> np.ndarray:
    """Return one (64, 64, 3) uint8 image of `food` at spoilage level `t` (0 fresh, 1 rotten)."""
    drift = float(np.clip((t - SPOIL_ONSET) / (BROWN_FULL - SPOIL_ONSET), 0.0, 1.0))
    colour = (1 - drift) * np.array(FOODS[food], dtype=float) + drift * np.array(BROWN, dtype=float)
    fruit = np.broadcast_to(colour, (SIZE, SIZE, 3)).copy()
    for y, x, t_appear in _spots(food):
        if t >= t_appear:
            grow = min(1.0, (t - t_appear) / (1.0 - t_appear))
            radius = SPOT_RADIUS[0] + (SPOT_RADIUS[1] - SPOT_RADIUS[0]) * grow
            fruit[(_YY - y) ** 2 + (_XX - x) ** 2 <= radius ** 2] = MOULD
    fruit += np.random.default_rng((_food_index(food), frame)).normal(0.0, NOISE_SD, fruit.shape)
    image = np.full((SIZE, SIZE, 3), BACKGROUND, dtype=np.uint8)
    image[SHAPE] = np.clip(fruit[SHAPE], 0, 255).round().astype(np.uint8)
    return image


def make_stream(food: str, n_fresh: int, n_spoil: int) -> list[tuple[np.ndarray, float, bool]]:
    """Return `n_fresh` frames at t = 0, then `n_spoil` frames with t ramping 0.3 to 1.0, as (image, t, is_spoiled)."""
    ts = [0.0] * n_fresh + list(np.linspace(SPOIL_ONSET, 1.0, n_spoil))
    return [(make_image(food, t, i), float(t), t >= SPOIL_ONSET) for i, t in enumerate(ts)]


def fruit_mask(image: np.ndarray) -> np.ndarray:
    """Return a bool (64, 64) mask that is True wherever the pixel differs from the background."""
    return np.any(np.abs(image.astype(int) - np.array(BACKGROUND)) > 10, axis=2)
