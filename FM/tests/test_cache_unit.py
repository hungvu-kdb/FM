"""Unit tests for :class:`facial_recognition.cache.EncodingCache`.

These example-based tests cover the cache's behavior on missing/corrupt files
and the file-signature staleness check.

Validates: Requirements 2.3, 2.4
"""

from __future__ import annotations

import os

import numpy as np

from facial_recognition.cache import EncodingCache
from facial_recognition.models import CacheEntry, ENCODING_DIM


def test_load_returns_empty_for_nonexistent_path(tmp_path) -> None:
    """load() returns {} when the cache file does not exist.

    Validates: Requirements 2.3
    """
    cache_path = tmp_path / "does_not_exist.npz"
    assert not cache_path.exists()

    cache = EncodingCache(str(cache_path))

    assert cache.load() == {}


def test_load_returns_empty_for_corrupt_file(tmp_path) -> None:
    """load() returns {} when the cache file contains garbage (non-npz) bytes.

    Validates: Requirements 2.3
    """
    cache_path = tmp_path / "corrupt.npz"
    # Write random non-npz bytes so np.load raises a decode/schema error,
    # which the cache must swallow and treat as an empty cache.
    cache_path.write_bytes(b"\x00\x01\x02not a real npz file\xff\xfe\xfd" * 8)

    cache = EncodingCache(str(cache_path))

    assert cache.load() == {}


def test_signature_detected_stale_when_file_changes(tmp_path) -> None:
    """A CacheEntry is stale when the current file signature differs.

    Builds a CacheEntry from a real file's signature, then mutates the file so
    its size and mtime change, and asserts the freshly computed signature no
    longer matches the stored one. Also asserts that an unchanged file's
    signature matches the stored entry (fresh case).

    Validates: Requirements 2.4
    """
    image_path = tmp_path / "face.png"
    image_path.write_bytes(b"original image content")

    size_bytes, mtime = EncodingCache.file_signature(str(image_path))
    entry = CacheEntry(
        image_path=str(image_path),
        size_bytes=size_bytes,
        mtime=mtime,
        encoding=np.zeros(ENCODING_DIM, dtype=np.float64),
    )

    # Fresh: unchanged file -> signature matches the stored one.
    assert EncodingCache.file_signature(str(image_path)) == entry.signature

    # Mutate the file so both size and mtime change.
    image_path.write_bytes(b"completely different and longer image content")
    # Force a distinct mtime in case the filesystem clock resolution is coarse.
    new_mtime = mtime + 100.0
    os.utime(str(image_path), (new_mtime, new_mtime))

    # Stale: current signature differs from the stored signature.
    assert EncodingCache.file_signature(str(image_path)) != entry.signature
