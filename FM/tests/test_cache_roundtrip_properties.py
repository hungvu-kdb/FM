"""Property-based tests for :class:`facial_recognition.cache.EncodingCache`.

These tests exercise the save/load round-trip of the on-disk encoding cache
across many randomly generated sets of cache entries using Hypothesis.

Property 8: Cache round-trip equivalence
    For any set of valid cache entries, ``save`` then ``load`` produces an
    equivalent set: the same set of keys, matching ``size_bytes`` and ``mtime``
    per entry, and encodings that compare equal under ``np.allclose``.

Validates: Requirements 2.1, 2.2
"""

from __future__ import annotations

import os
import shutil
import tempfile
from typing import Dict

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.extra import numpy as hnp

from facial_recognition.cache import EncodingCache
from facial_recognition.models import CacheEntry, ENCODING_DIM


# Non-empty image-path strings used as both the dict key and the entry's
# ``image_path``. Restricting to printable text keeps the keys legible while
# still spanning a wide space; ``unique=True`` on the dict enforces uniqueness.
_path_strategy = st.text(
    alphabet=st.characters(min_codepoint=33, max_codepoint=126),
    min_size=1,
    max_size=40,
)

# Finite 128-d float embeddings with a bounded magnitude so float64 serialization
# round-trips exactly without overflow concerns.
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

# A file signature: size_bytes >= 0 and mtime > 0 (per CacheEntry validation).
_size_strategy = st.integers(min_value=0, max_value=2**40)
_mtime_strategy = st.floats(
    min_value=1e-3,
    max_value=4e9,
    allow_nan=False,
    allow_infinity=False,
    width=64,
)


@st.composite
def _cache_entries(draw) -> Dict[str, CacheEntry]:
    """Build a ``{image_path: CacheEntry}`` dict with unique, consistent keys.

    The dict key always equals ``entry.image_path`` so the saved index and the
    loaded keys are directly comparable.
    """
    paths = draw(
        st.lists(_path_strategy, min_size=0, max_size=10, unique=True)
    )
    entries: Dict[str, CacheEntry] = {}
    for path in paths:
        entries[path] = CacheEntry(
            image_path=path,
            size_bytes=draw(_size_strategy),
            mtime=draw(_mtime_strategy),
            encoding=draw(_encoding_strategy),
        )
    return entries


@settings(max_examples=150)
@given(entries=_cache_entries())
def test_cache_save_load_round_trip(entries: Dict[str, CacheEntry]) -> None:
    """save() then load() yields an equivalent set of cache entries.

    Validates: Requirements 2.1, 2.2
    """
    # Hypothesis discourages function-scoped pytest fixtures (e.g. tmp_path),
    # so create and clean up the temp directory inside the test body.
    tmp_dir = tempfile.mkdtemp(prefix="cache_roundtrip_")
    try:
        cache_path = os.path.join(tmp_dir, "encodings.npz")
        cache = EncodingCache(cache_path)

        cache.save(entries)
        loaded = cache.load()

        # Same set of keys.
        assert set(loaded.keys()) == set(entries.keys())

        # Per-entry equivalence of signature and encoding.
        for key, original in entries.items():
            result = loaded[key]
            assert result.image_path == original.image_path
            assert result.size_bytes == original.size_bytes
            assert result.mtime == original.mtime
            assert np.allclose(result.encoding, original.encoding)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
