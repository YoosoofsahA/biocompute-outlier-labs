"""Silicon half: edge detector. Owner: role 3 (Silicon).

STUB: always returns 0. Replace with a Sobel filter on greyscale, counting fruit-mask pixels whose edge strength is
above a threshold (fresh-eyes-spec.md section 2).
"""
from __future__ import annotations

import numpy as np


def edge_score(image: np.ndarray) -> float:
    """Return how much edge (spot, crack, mould) there is inside the fruit. Higher means more."""
    return 0.0
