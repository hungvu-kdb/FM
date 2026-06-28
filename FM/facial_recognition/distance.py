"""Distance and similarity math for the facial recognition tool.

This module provides the pure, vectorized numeric helpers used by the
:class:`~facial_recognition.matcher.Matcher`:

- :func:`euclidean_distances` -- row-wise L2 distance between every row of an
  ``(N, 128)`` embedding matrix and a single ``(128,)`` query embedding.
- :func:`distance_to_similarity` -- map a non-negative distance to a bounded
  similarity score in ``(0, 1]``.

Both functions depend only on ``numpy`` and never mutate their inputs, so they
remain importable and testable without the native ``face_recognition``/``dlib``
stack.
"""

from __future__ import annotations

import numpy as np

from .models import ENCODING_DIM


def euclidean_distances(matrix: np.ndarray, query: np.ndarray) -> np.ndarray:
    """Compute the row-wise Euclidean (L2) distance from ``query`` to each row.

    Args:
        matrix: Embedding matrix of shape ``(N, 128)``.
        query: Query embedding of shape ``(128,)``.

    Returns:
        A 1-D array of shape ``(N,)`` where ``out[i] == ||matrix[i] - query||_2``.
        All values are ``>= 0``.

    Raises:
        ValueError: if ``matrix`` is not 2-D with ``ENCODING_DIM`` columns or
            ``query`` does not have shape ``(ENCODING_DIM,)``.

    Notes:
        The inputs are never mutated. The difference is computed into a fresh
        array via broadcasting, so ``matrix`` and ``query`` are left untouched.
    """
    if matrix.ndim != 2 or matrix.shape[1] != ENCODING_DIM:
        raise ValueError(
            f"matrix must have shape (N, {ENCODING_DIM}), got {matrix.shape}"
        )
    if query.shape != (ENCODING_DIM,):
        raise ValueError(
            f"query must have shape ({ENCODING_DIM},), got {query.shape}"
        )

    # Broadcasting subtraction produces a new (N, 128) array; inputs are not
    # modified. np.linalg.norm over axis=1 yields the per-row L2 distance.
    diff = matrix - query
    return np.linalg.norm(diff, axis=1)


def distance_to_similarity(distance: float) -> float:
    """Map a face ``distance`` to a bounded similarity score.

    Args:
        distance: A non-negative Euclidean distance.

    Returns:
        ``1.0 / (1.0 + distance)``, a value in ``(0, 1]`` that is
        monotonically non-increasing in ``distance``. A distance of ``0``
        yields ``1.0``.
    """
    return 1.0 / (1.0 + distance)
