"""Property-based tests for cache equivalence (cold vs warm matching).

These tests verify that the on-disk encoding cache is purely a performance
optimization: matching an unchanged gallery yields identical ``MatchResult``s
whether the gallery encodings were freshly computed (cold cache) or reloaded
from a populated cache (warm cache).

Property 5: Cache equivalence
    For an unchanged gallery, matching with a freshly built cache and matching
    with a reused cache produce identical ``MatchResult``s.

Validates: Requirements 6.1
"""

from __future__ import annotations

import os
import shutil
import tempfile
from typing import Dict, List

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.extra import numpy as hnp

from facial_recognition.cache import EncodingCache
from facial_recognition.gallery import GalleryManager
from facial_recognition.matcher import Matcher
from facial_recognition.models import ENCODING_DIM


# Unique gallery basenames. ASCII letters/digits only so the names are valid
# Windows filenames and case-insensitively distinct on disk.
_basename_strategy = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    min_size=1,
    max_size=12,
)

# Finite, bounded 128-d float embeddings so distances stay well-defined and
# the float64 cache round-trip is exact.
_encoding_elements = st.floats(
    min_value=-1e3,
    max_value=1e3,
    allow_nan=False,
    allow_infinity=False,
    width=64,
)
_encoding_strategy = hnp.arrays(
    dtype=np.float64,
    shape=ENCODING_DIM,
    elements=_encoding_elements,
)
_query_strategy = hnp.arrays(
    dtype=np.float64,
    shape=ENCODING_DIM,
    elements=_encoding_elements,
)


class _DeterministicMockEncoder:
    """Mock encoder returning a fixed embedding per basename.

    ``encode_image`` looks up the predetermined embedding for the file's
    basename, so the same path always yields the same vector regardless of the
    actual pixel content. Calls are counted so tests can assert reuse.
    """

    def __init__(self, embeddings_by_basename: Dict[str, np.ndarray]) -> None:
        self._embeddings = embeddings_by_basename
        self.call_count = 0
        self.called_paths: List[str] = []

    def encode_image(self, image_path: str):  # noqa: ANN201 - mirrors Encoder API
        self.call_count += 1
        self.called_paths.append(image_path)
        return self._embeddings[os.path.basename(image_path)]


class _FailingMockEncoder:
    """Mock encoder that fails if ``encode_image`` is ever invoked.

    Used for the warm run to prove that a populated, signature-matching cache
    is reused and the encoder is never called.
    """

    def __init__(self) -> None:
        self.call_count = 0

    def encode_image(self, image_path: str):  # noqa: ANN201 - mirrors Encoder API
        self.call_count += 1
        raise AssertionError(
            f"warm-cache encoder should not be called, but was for {image_path!r}"
        )


@st.composite
def _gallery_and_query(draw):
    """Generate (embeddings_by_basename, query, top_k) for one example.

    Produces a set of unique gallery basenames each mapped to a deterministic
    128-d embedding, plus a query vector and a ``top_k`` spanning the gallery.
    """
    # Filesystems on Windows are case-insensitive, so two basenames differing
    # only by case would collide on disk. Enforce case-insensitive uniqueness
    # of the resulting ``.png`` filenames so every generated file is distinct.
    raw_basenames = draw(
        st.lists(_basename_strategy, min_size=1, max_size=6)
    )
    embeddings: Dict[str, np.ndarray] = {}
    seen_lower: set[str] = set()
    for name in raw_basenames:
        filename = f"{name}.png"
        key = filename.lower()
        if key in seen_lower:
            continue
        seen_lower.add(key)
        embeddings[filename] = draw(_encoding_strategy)
    query = draw(_query_strategy)
    top_k = draw(st.integers(min_value=1, max_value=len(embeddings) + 2))
    return embeddings, query, top_k


@settings(max_examples=100, deadline=None)
@given(data=_gallery_and_query())
def test_cold_and_warm_cache_produce_identical_results(data) -> None:
    """Cold-cache and warm-cache matching yield identical MatchResults.

    Validates: Requirements 6.1
    """
    embeddings_by_basename, query, top_k = data

    # Hypothesis discourages function-scoped pytest fixtures (e.g. tmp_path),
    # so create and clean up the temp directories inside the test body.
    tmp_dir = tempfile.mkdtemp(prefix="cache_equiv_")
    try:
        from PIL import Image

        gallery_dir = os.path.join(tmp_dir, "gallery")
        os.makedirs(gallery_dir, exist_ok=True)

        # Write small real PNG files so signatures are stable across runs. The
        # mock encoder ignores pixel content and keys off the basename.
        for filename in embeddings_by_basename:
            Image.new("RGB", (8, 8)).save(os.path.join(gallery_dir, filename))

        cache_path = os.path.join(tmp_dir, "encodings.npz")
        matcher = Matcher(threshold=0.6)

        # COLD run: fresh cache (file does not exist yet). The encoder is
        # invoked for every image, and the cache is written to disk.
        cold_encoder = _DeterministicMockEncoder(embeddings_by_basename)
        cold_cache = EncodingCache(cache_path)
        gallery_cold = GalleryManager(cold_encoder, cold_cache).load_gallery(
            gallery_dir
        )
        results_cold = matcher.rank(query, gallery_cold, top_k=top_k)

        # The cold run must have encoded every gallery image and populated cache.
        assert cold_encoder.call_count == len(embeddings_by_basename)
        assert os.path.exists(cache_path)

        # WARM run: new cache instance over the SAME (now populated) path. The
        # encoder must never be called because every file signature matches.
        warm_encoder = _FailingMockEncoder()
        warm_cache = EncodingCache(cache_path)
        gallery_warm = GalleryManager(warm_encoder, warm_cache).load_gallery(
            gallery_dir
        )
        results_warm = matcher.rank(query, gallery_warm, top_k=top_k)

        # Cache reuse proof: the warm encoder was never invoked.
        assert warm_encoder.call_count == 0

        # Results must be identical in length and per-entry content/order.
        assert len(results_cold) == len(results_warm)
        for cold, warm in zip(results_cold, results_warm):
            assert cold.filename == warm.filename
            assert np.isclose(cold.distance, warm.distance)
            assert np.isclose(cold.similarity, warm.similarity)
            assert cold.is_match == warm.is_match
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
