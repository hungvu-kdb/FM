"""Property-based tests for :meth:`facial_recognition.matcher.Matcher.rank`.

These tests exercise a universal ordering property of ranking across many
randomly generated galleries and queries using Hypothesis.

Property 2: Ranking order
    For all queries ``q`` and galleries ``G``, ``rank(q, G, k)`` is sorted by
    non-decreasing distance (each result's distance is ``<=`` the next).

Validates: Requirements 4.2
"""

from __future__ import annotations

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.extra import numpy as hnp

from facial_recognition.matcher import Matcher
from facial_recognition.models import ENCODING_DIM, GalleryEncodingSet


# Finite float64 embeddings with a bounded magnitude. Bounding the range keeps
# the squared differences well away from float overflow while still spanning a
# wide space of positive, negative, and zero components.
_FLOAT_ELEMENTS = st.floats(
    min_value=-1e6,
    max_value=1e6,
    allow_nan=False,
    allow_infinity=False,
    width=64,
)


@st.composite
def _gallery_and_query(draw: st.DrawFn) -> tuple[GalleryEncodingSet, np.ndarray]:
    """Build a non-empty ``GalleryEncodingSet`` and a ``(128,)`` query.

    The gallery has ``N >= 1`` rows, unique ``imgN.png`` filenames parallel to
    the rows of an ``(N, 128)`` matrix, and a single ``(128,)`` query embedding.
    """
    n = draw(st.integers(min_value=1, max_value=30))
    matrix = draw(
        hnp.arrays(dtype=np.float64, shape=(n, ENCODING_DIM), elements=_FLOAT_ELEMENTS)
    )
    query = draw(
        hnp.arrays(dtype=np.float64, shape=(ENCODING_DIM,), elements=_FLOAT_ELEMENTS)
    )
    filenames = [f"img{i}.png" for i in range(n)]
    gallery = GalleryEncodingSet(filenames=filenames, matrix=matrix)
    return gallery, query


@settings(max_examples=200)
@given(data=_gallery_and_query(), top_k=st.integers(min_value=1, max_value=40))
def test_rank_returns_non_decreasing_distances(
    data: tuple[GalleryEncodingSet, np.ndarray], top_k: int
) -> None:
    """rank(q, G, k) results are sorted by non-decreasing distance.

    Validates: Requirements 4.2
    """
    gallery, query = data
    matcher = Matcher()

    results = matcher.rank(query, gallery, top_k=top_k)

    distances = [r.distance for r in results]
    for earlier, later in zip(distances, distances[1:]):
        assert earlier <= later, (
            f"ranking not non-decreasing: {earlier} > {later} in {distances}"
        )
