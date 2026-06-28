"""Unit tests for the core data models in ``facial_recognition.models``.

These tests cover the validation rules from the design's "Data Models" section:

- ``CacheEntry`` encoding shape and field validation, plus the ``signature``
  property.
- ``GalleryEncodingSet`` matrix/filenames length agreement, duplicate-filename
  rejection, and ``__len__`` behavior.
- ``MatchResult`` distance/similarity bounds.

Validates: Requirements 3.6
"""

from __future__ import annotations

import numpy as np
import pytest

from facial_recognition.models import (
    ENCODING_DIM,
    CacheEntry,
    GalleryEncodingSet,
    MatchResult,
    validate_encoding,
    validate_matrix,
    validate_no_duplicate_filenames,
)


def _encoding(value: float = 0.0) -> np.ndarray:
    """Return a valid ``(128,)`` encoding filled with ``value``."""
    return np.full((ENCODING_DIM,), value, dtype=float)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------
class TestValidateEncoding:
    def test_accepts_correct_shape(self) -> None:
        validate_encoding(_encoding())  # should not raise

    @pytest.mark.parametrize(
        "shape",
        [(127,), (129,), (1, 128), (128, 1), (64, 2), ()],
    )
    def test_rejects_wrong_shape(self, shape: tuple[int, ...]) -> None:
        with pytest.raises(ValueError):
            validate_encoding(np.zeros(shape))

    def test_rejects_non_array(self) -> None:
        with pytest.raises(TypeError):
            validate_encoding([0.0] * ENCODING_DIM)  # type: ignore[arg-type]


class TestValidateMatrix:
    def test_accepts_correct_shape(self) -> None:
        validate_matrix(np.zeros((3, ENCODING_DIM)), 3)
        validate_matrix(np.empty((0, ENCODING_DIM)), 0)

    @pytest.mark.parametrize(
        "shape, n_rows",
        [
            ((2, ENCODING_DIM), 3),  # row count mismatch
            ((3, 127), 3),           # wrong embedding width
            ((3,), 3),               # not 2-D
        ],
    )
    def test_rejects_wrong_shape(self, shape: tuple[int, ...], n_rows: int) -> None:
        with pytest.raises(ValueError):
            validate_matrix(np.zeros(shape), n_rows)

    def test_rejects_non_array(self) -> None:
        with pytest.raises(TypeError):
            validate_matrix([[0.0] * ENCODING_DIM], 1)  # type: ignore[arg-type]


class TestValidateNoDuplicateFilenames:
    def test_accepts_unique(self) -> None:
        validate_no_duplicate_filenames(["a.png", "b.png", "c.png"])
        validate_no_duplicate_filenames([])

    def test_rejects_duplicates(self) -> None:
        with pytest.raises(ValueError):
            validate_no_duplicate_filenames(["a.png", "b.png", "a.png"])


# ---------------------------------------------------------------------------
# CacheEntry
# ---------------------------------------------------------------------------
class TestCacheEntry:
    def test_valid_entry(self) -> None:
        entry = CacheEntry("img.png", 100, 12.5, _encoding())
        assert entry.image_path == "img.png"
        assert entry.size_bytes == 100
        assert entry.mtime == 12.5

    def test_signature_property(self) -> None:
        entry = CacheEntry("img.png", 100, 12.5, _encoding())
        assert entry.signature == (100, 12.5)

    @pytest.mark.parametrize("shape", [(127,), (129,), (1, 128), ()])
    def test_rejects_wrong_encoding_shape(self, shape: tuple[int, ...]) -> None:
        with pytest.raises(ValueError):
            CacheEntry("img.png", 100, 12.5, np.zeros(shape))

    def test_rejects_empty_path(self) -> None:
        with pytest.raises(ValueError):
            CacheEntry("", 100, 12.5, _encoding())

    def test_rejects_negative_size(self) -> None:
        with pytest.raises(ValueError):
            CacheEntry("img.png", -1, 12.5, _encoding())

    def test_accepts_zero_size(self) -> None:
        entry = CacheEntry("img.png", 0, 12.5, _encoding())
        assert entry.size_bytes == 0

    @pytest.mark.parametrize("mtime", [0.0, -1.0])
    def test_rejects_non_positive_mtime(self, mtime: float) -> None:
        with pytest.raises(ValueError):
            CacheEntry("img.png", 100, mtime, _encoding())

    def test_is_frozen(self) -> None:
        entry = CacheEntry("img.png", 100, 12.5, _encoding())
        with pytest.raises(Exception):
            entry.size_bytes = 200  # type: ignore[misc]


# ---------------------------------------------------------------------------
# GalleryEncodingSet
# ---------------------------------------------------------------------------
class TestGalleryEncodingSet:
    def test_valid_set(self) -> None:
        gset = GalleryEncodingSet(
            ["a.png", "b.png"], np.zeros((2, ENCODING_DIM))
        )
        assert gset.filenames == ["a.png", "b.png"]
        assert gset.matrix.shape == (2, ENCODING_DIM)

    def test_default_empty(self) -> None:
        gset = GalleryEncodingSet()
        assert len(gset) == 0
        assert gset.matrix.shape == (0, ENCODING_DIM)

    def test_len_matches_filenames(self) -> None:
        gset = GalleryEncodingSet(
            ["a.png", "b.png", "c.png"], np.zeros((3, ENCODING_DIM))
        )
        assert len(gset) == 3

    def test_rejects_matrix_filenames_length_mismatch(self) -> None:
        with pytest.raises(ValueError):
            GalleryEncodingSet(["a.png", "b.png"], np.zeros((3, ENCODING_DIM)))

    def test_rejects_wrong_embedding_width(self) -> None:
        with pytest.raises(ValueError):
            GalleryEncodingSet(["a.png"], np.zeros((1, ENCODING_DIM - 1)))

    def test_rejects_duplicate_filenames(self) -> None:
        with pytest.raises(ValueError):
            GalleryEncodingSet(
                ["a.png", "a.png"], np.zeros((2, ENCODING_DIM))
            )


# ---------------------------------------------------------------------------
# MatchResult
# ---------------------------------------------------------------------------
class TestMatchResult:
    def test_valid_result(self) -> None:
        result = MatchResult("a.png", 0.4, 0.7, True)
        assert result.filename == "a.png"
        assert result.distance == 0.4
        assert result.similarity == 0.7
        assert result.is_match is True

    def test_rejects_empty_filename(self) -> None:
        with pytest.raises(ValueError):
            MatchResult("", 0.4, 0.7, True)

    def test_rejects_negative_distance(self) -> None:
        with pytest.raises(ValueError):
            MatchResult("a.png", -0.1, 0.7, True)

    def test_accepts_zero_distance(self) -> None:
        result = MatchResult("a.png", 0.0, 1.0, True)
        assert result.distance == 0.0

    @pytest.mark.parametrize("similarity", [-0.01, 1.01, 2.0, -1.0])
    def test_rejects_out_of_bounds_similarity(self, similarity: float) -> None:
        with pytest.raises(ValueError):
            MatchResult("a.png", 0.4, similarity, True)

    @pytest.mark.parametrize("similarity", [0.0, 0.5, 1.0])
    def test_accepts_boundary_similarity(self, similarity: float) -> None:
        result = MatchResult("a.png", 0.4, similarity, False)
        assert result.similarity == similarity
