"""Property-based tests for :func:`facial_recognition.distance.distance_to_similarity`.

These tests exercise universal mathematical properties of the similarity
mapping across many randomly generated inputs using Hypothesis.

Property 4: Similarity monotonicity and bounds
    For all distances ``d1 <= d2`` (both ``>= 0``),
    ``similarity(d1) >= similarity(d2)``, the result lies in ``(0, 1]``, and
    ``similarity(0) == 1.0``.

Validates: Requirements 4.6
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from facial_recognition.distance import distance_to_similarity


# Non-negative finite distances. Bounding the upper end keeps ``1 + distance``
# well away from float overflow while still spanning a wide range of magnitudes.
_distance_strategy = st.floats(
    min_value=0.0,
    max_value=1e12,
    allow_nan=False,
    allow_infinity=False,
    width=64,
)


@settings(max_examples=200)
@given(_distance_strategy, _distance_strategy)
def test_similarity_monotonicity_and_bounds(a: float, b: float) -> None:
    """For ordered d1 <= d2, similarity is non-increasing and within (0, 1].

    Validates: Requirements 4.6
    """
    d1, d2 = sorted((a, b))

    s1 = distance_to_similarity(d1)
    s2 = distance_to_similarity(d2)

    # Monotonic non-increasing: a larger distance never yields a larger score.
    assert s1 >= s2

    # Bounds (0, 1]: similarity is strictly positive and never exceeds 1.
    for s in (s1, s2):
        assert 0.0 < s <= 1.0


@settings(max_examples=200)
@given(_distance_strategy)
def test_similarity_within_bounds(distance: float) -> None:
    """Every non-negative distance maps into the half-open interval (0, 1].

    Validates: Requirements 4.6
    """
    s = distance_to_similarity(distance)
    assert 0.0 < s <= 1.0


def test_similarity_at_zero_is_one() -> None:
    """A distance of exactly 0 yields a similarity of exactly 1.0.

    Validates: Requirements 4.6
    """
    assert distance_to_similarity(0.0) == 1.0
