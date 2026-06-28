"""Property-based tests for :meth:`facial_recognition.matcher.Matcher.find_best_match`.

These tests exercise a universal minimality property of best-match selection
across many randomly generated galleries and queries using Hypothesis.

Property 1: Minimality of best match
    For all non-empty galleries ``G`` and queries ``q``,
    ``find_best_match(q, G).distance == min`` of the row-wise Euclidean
    distances from ``q`` to every embedding in ``G``.

Validates: Requirements 4.1
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
@given(data=_gallery_and_query())
def test_find_best_match_distance_equals_brute_force_min(
    data: tuple[GalleryEncodingSet, np.ndarray],
) -> None:
    """find_best_match(q, G).distance equals the brute-force minimum distance.

    Validates: Requirements 4.1
    """
    gallery, query = data
    matcher = Matcher()

    best = matcher.find_best_match(query, gallery)

    # Non-empty gallery -> a result is always returned.
    assert best is not None

    brute_force_min = float(np.linalg.norm(gallery.matrix - query, axis=1).min())

    assert np.isclose(best.distance, brute_force_min), (
        f"best match distance {best.distance} != brute-force min {brute_force_min}"
    )
