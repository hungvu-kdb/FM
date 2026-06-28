"""Property-based tests for the ``is_match`` flag of :class:`MatchResult`.

These tests exercise the match-flag correctness property of
:meth:`facial_recognition.matcher.Matcher.rank` across many randomly generated
galleries, queries, and thresholds using Hypothesis.

Property 13: Match flag correctness
    For any distance ``d`` and threshold ``t``, the resulting
    ``MatchResult.is_match`` is true exactly when ``d <= t``.

Validates: Requirements 4.7
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
    """Build a non-empty ``GalleryEncodingSet`` plus a ``(128,)`` query.

    ``N >= 1`` so that ``rank`` returns at least one ``MatchResult`` whose
    ``is_match`` flag can be checked.
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
@given(
    data=_gallery_and_query(),
    threshold=st.floats(
        min_value=0.0, max_value=5.0, allow_nan=False, allow_infinity=False
    ),
    top_k=st.integers(min_value=1, max_value=40),
)
def test_is_match_iff_distance_within_threshold(
    data: tuple[GalleryEncodingSet, np.ndarray],
    threshold: float,
    top_k: int,
) -> None:
    """Every result's ``is_match`` equals ``distance <= threshold``.

    Validates: Requirements 4.7
    """
    gallery, query = data
    matcher = Matcher(threshold=threshold)

    results = matcher.rank(query, gallery, top_k=top_k)

    for result in results:
        expected = result.distance <= threshold
        assert result.is_match == expected, (
            f"is_match={result.is_match} but distance={result.distance} "
            f"<= threshold={threshold} is {expected}"
        )
