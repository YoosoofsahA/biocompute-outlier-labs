"""Silicon half: edge detector. Owner: role 3 (Silicon).

Sobel filter on greyscale, then count the fruit pixels whose edge strength is above EDGE_THRESHOLD. Mould spots add
sharp edges, while smooth browning adds none, so this half stays blind to early colour drift. Calibration and the
alarm itself live in alarm.py.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

from images import fruit_mask

GREY_WEIGHTS = np.array([0.299, 0.587, 0.114])   # Rec. 601 luma
EDGE_THRESHOLD = 100.0                           # Sobel magnitude; a 25-level grey step gives about 100
RIM = np.ones((3, 3), dtype=bool)                # matches the Sobel footprint


def edge_score(image: np.ndarray) -> float:
    """Return how much edge (spot, crack, mould) there is inside the fruit. Higher means more."""
    grey = image.astype(float) @ GREY_WEIGHTS
    strength = np.hypot(ndimage.sobel(grey, axis=0), ndimage.sobel(grey, axis=1))
    # Drop the rim of the mask: the fruit's outline gets stronger against the background as the fruit browns, and
    # counting it would let colour drift trip the silicon alarm.
    inside = ndimage.binary_erosion(fruit_mask(image), structure=RIM)
    return float(np.count_nonzero(strength[inside] > EDGE_THRESHOLD))
