"""Property-based tests for :mod:`facial_recognition.distance`.

These tests exercise universal mathematical properties of the distance math
across many randomly generated inputs using Hypothesis.

Property 6: Distance symmetry and non-negativity
    For all encodings ``a, b``, ``distance(a, b) == distance(b, a) >= 0``.

Validates: Requirements 4.5
"""

from __future__ import annotations

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.extra import numpy as hnp

from facial_recognition.distance import euclidean_distances
from facial_recognition.models import ENCODING_DIM


def _distance(a: np.ndarray, b: np.ndarray) -> float:
    """Distance between two single ``(128,)`` encodings via ``euclidean_distances``.

    ``a`` is treated as a ``(1, 128)`` matrix and ``b`` as the ``(128,)`` query,
    so the public matrix/query API is what gets exercised.
    """
    return float(euclidean_distances(a.reshape(1, ENCODING_DIM), b)[0])


# Finite float64 vectors with a bounded magnitude. Bounding the range keeps the
# squared differences well away from float overflow while still spanning a wide
# space of positive, negative, and zero components.
_encoding_strategy = hnp.arrays(
    dtype=np.float64,
    shape=ENCODING_DIM,
    elements=st.floats(
        min_value=-1e6,
        max_value=1e6,
        allow_nan=False,
        allow_infinity=False,
        width=64,
    ),
)


@settings(max_examples=200)
@given(a=_encoding_strategy, b=_encoding_strategy)
def test_distance_symmetry_non_negativity_and_brute_force(
    a: np.ndarray, b: np.ndarray
) -> None:
    """distance(a, b) == distance(b, a) >= 0 and matches a brute-force L2.

    Validates: Requirements 4.5
    """
    d_ab = _distance(a, b)
    d_ba = _distance(b, a)

    # Non-negativity: an L2 norm is always >= 0 and never NaN.
    assert d_ab >= 0.0
    assert np.isfinite(d_ab)

    # Symmetry: ||a - b|| == ||b - a||.
    assert d_ab == d_ba or np.isclose(d_ab, d_ba, rtol=1e-9, atol=1e-9)

    # Agreement with an independent brute-force numpy L2 computation.
    brute = float(np.linalg.norm(a - b))
    assert np.isclose(d_ab, brute, rtol=1e-9, atol=1e-9)
