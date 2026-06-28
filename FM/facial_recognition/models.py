"""Core data models for the facial recognition tool.

This module defines the pure data structures used across the pipeline:

- :class:`CacheEntry`        -- one persisted gallery embedding plus its file signature.
- :class:`GalleryEncodingSet` -- the in-memory set of gallery embeddings.
- :class:`MatchResult`       -- the outcome of comparing a query against a gallery entry.

The models carry their own validation rules (derived from the design's
"Data Models" section) and a few reusable validation helpers. They depend only
on ``numpy`` so they remain importable without the native ``face_recognition``
/``dlib`` stack.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

import numpy as np

# The face_recognition / dlib encoder produces a fixed-length embedding.
ENCODING_DIM = 128


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------
def validate_encoding(encoding: np.ndarray) -> None:
    """Validate that ``encoding`` is a 1-D embedding of shape ``(128,)``.

    Raises:
        TypeError: if ``encoding`` is not a numpy array.
        ValueError: if the shape is not exactly ``(ENCODING_DIM,)``.
    """
    if not isinstance(encoding, np.ndarray):
        raise TypeError(
            f"encoding must be a numpy.ndarray, got {type(encoding).__name__}"
        )
    if encoding.shape != (ENCODING_DIM,):
        raise ValueError(
            f"encoding must have shape ({ENCODING_DIM},), got {encoding.shape}"
        )


def validate_matrix(matrix: np.ndarray, n_rows: int) -> None:
    """Validate that ``matrix`` has shape ``(n_rows, 128)``.

    Raises:
        TypeError: if ``matrix`` is not a numpy array.
        ValueError: if the shape is not ``(n_rows, ENCODING_DIM)``.
    """
    if not isinstance(matrix, np.ndarray):
        raise TypeError(
            f"matrix must be a numpy.ndarray, got {type(matrix).__name__}"
        )
    if matrix.shape != (n_rows, ENCODING_DIM):
        raise ValueError(
            f"matrix must have shape ({n_rows}, {ENCODING_DIM}), got {matrix.shape}"
        )


def validate_no_duplicate_filenames(filenames: list[str]) -> None:
    """Validate that ``filenames`` contains no duplicate entries.

    Raises:
        ValueError: if any filename appears more than once.
    """
    seen: set[str] = set()
    duplicates: set[str] = set()
    for name in filenames:
        if name in seen:
            duplicates.add(name)
        seen.add(name)
    if duplicates:
        raise ValueError(
            f"filenames must be unique; duplicates found: {sorted(duplicates)}"
        )


# ---------------------------------------------------------------------------
# Model 1: CacheEntry
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CacheEntry:
    """A persisted gallery embedding keyed by its source file signature.

    Attributes:
        image_path: Absolute path to the gallery image.
        size_bytes: File size in bytes at encode time.
        mtime: File modification time at encode time.
        encoding: 128-d float embedding for the image's face.

    Validation Rules:
        - ``encoding`` must have shape ``(128,)``.
        - ``size_bytes >= 0`` and ``mtime > 0``.
        - ``image_path`` must be non-empty.
    """

    image_path: str
    size_bytes: int
    mtime: float
    encoding: np.ndarray

    def __post_init__(self) -> None:
        if not self.image_path:
            raise ValueError("image_path must be non-empty")
        if self.size_bytes < 0:
            raise ValueError(f"size_bytes must be >= 0, got {self.size_bytes}")
        if self.mtime <= 0:
            raise ValueError(f"mtime must be > 0, got {self.mtime}")
        validate_encoding(self.encoding)

    @property
    def signature(self) -> Tuple[int, float]:
        """Return the ``(size_bytes, mtime)`` file signature for staleness checks."""
        return (self.size_bytes, self.mtime)


# ---------------------------------------------------------------------------
# Model 2: GalleryEncodingSet
# ---------------------------------------------------------------------------
@dataclass
class GalleryEncodingSet:
    """The in-memory set of gallery embeddings.

    ``filenames[i]`` is the gallery filename whose embedding is row ``i`` of
    ``matrix``.

    Attributes:
        filenames: Filenames parallel to the rows of ``matrix``.
        matrix: Embedding matrix of shape ``(len(filenames), 128)``.

    Validation Rules:
        - ``matrix.shape == (len(filenames), 128)``.
        - ``filenames`` contains no duplicates.
        - Row ``i`` of ``matrix`` is the encoding for ``filenames[i]``.
    """

    filenames: list[str] = field(default_factory=list)
    matrix: np.ndarray = field(
        default_factory=lambda: np.empty((0, ENCODING_DIM))
    )

    def __post_init__(self) -> None:
        validate_no_duplicate_filenames(self.filenames)
        validate_matrix(self.matrix, len(self.filenames))

    def __len__(self) -> int:
        """Return the number of gallery entries (equivalently, matrix rows)."""
        return len(self.filenames)


# ---------------------------------------------------------------------------
# Model 3: MatchResult
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MatchResult:
    """The outcome of comparing a query embedding against one gallery entry.

    Attributes:
        filename: Gallery filename of the match.
        distance: Euclidean distance to the query (lower = more similar).
        similarity: Normalized score in ``[0, 1]`` (higher = more similar).
        is_match: True if ``distance <= threshold`` (same-person flag).

    Validation Rules:
        - ``distance >= 0``.
        - ``0 <= similarity <= 1``.
    """

    filename: str
    distance: float
    similarity: float
    is_match: bool

    def __post_init__(self) -> None:
        if not self.filename:
            raise ValueError("filename must be non-empty")
        if self.distance < 0:
            raise ValueError(f"distance must be >= 0, got {self.distance}")
        if not (0.0 <= self.similarity <= 1.0):
            raise ValueError(
                f"similarity must be in [0, 1], got {self.similarity}"
            )
