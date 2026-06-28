"""Property-based tests for :meth:`facial_recognition.matcher.Matcher.rank`.

These tests exercise the ``top_k`` truncation property of ranking across many
randomly generated gallery sizes and ``top_k`` values using Hypothesis.

Property 11: top_k truncation
    For any gallery of size ``N`` and any non-negative ``top_k``,
    ``rank(q, G, top_k)`` returns exactly ``min(top_k, N)`` results. A
    ``top_k`` of ``0`` (or an empty gallery) yields an empty list.

Validates: Requirements 4.3
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
    """Build a ``GalleryEncodingSet`` with ``N >= 0`` rows and a ``(128,)`` query.

    ``N`` may be ``0`` (an empty gallery, with empty filenames and an
    ``(0, 128)`` matrix), exercising the empty-gallery truncation case.
    """
    n = draw(st.integers(min_value=0, max_value=30))
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
@given(data=_gallery_and_query(), top_k=st.integers(min_value=0, max_value=40))
def test_rank_returns_min_top_k_and_n_results(
    data: tuple[GalleryEncodingSet, np.ndarray], top_k: int
) -> None:
    """rank(q, G, top_k) returns exactly min(top_k, N) results.

    Validates: Requirements 4.3
    """
    gallery, query = data
    matcher = Matcher()

    results = matcher.rank(query, gallery, top_k=top_k)

    n = len(gallery)
    expected = min(top_k, n)
    assert len(results) == expected, (
        f"expected min(top_k={top_k}, N={n}) = {expected} results, "
        f"got {len(results)}"
    )
