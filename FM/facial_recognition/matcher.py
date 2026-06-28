"""Matcher: compare a query embedding against the gallery and rank results.

The :class:`Matcher` is a thin orchestration layer over the pure numeric
helpers in :mod:`facial_recognition.distance`. It computes the row-wise
distance from a query embedding to every gallery embedding, sorts ascending
(closest first), and wraps each candidate in a :class:`MatchResult`.
"""

from __future__ import annotations

from typing import List, Optional

import numpy as np

from .distance import distance_to_similarity, euclidean_distances
from .models import GalleryEncodingSet, MatchResult


class Matcher:
    """Compare a query encoding against the gallery and rank by similarity."""

    def __init__(self, threshold: float = 0.6) -> None:
        """threshold: max distance to be considered the same person."""
        self.threshold = threshold

    def find_best_match(
        self, query: np.ndarray, gallery: GalleryEncodingSet
    ) -> Optional[MatchResult]:
        """Return the closest gallery entry, or ``None`` if the gallery is empty."""
        if len(gallery) == 0:
            return None
        results = self.rank(query, gallery, top_k=1)
        return results[0] if results else None

    def rank(
        self, query: np.ndarray, gallery: GalleryEncodingSet, top_k: int = 5
    ) -> List[MatchResult]:
        """Return the ``top_k`` closest entries sorted by ascending distance.

        ``len(result) == min(top_k, N)`` where ``N`` is the gallery size. A
        ``top_k`` of ``0`` (or an empty gallery) yields an empty list.
        """
        n = len(gallery)
        if n == 0 or top_k <= 0:
            return []

        distances = euclidean_distances(gallery.matrix, query)  # shape (N,)
        order = np.argsort(distances, kind="stable")            # closest first

        results: List[MatchResult] = []
        for i in order[:top_k]:
            d = float(distances[i])
            results.append(
                MatchResult(
                    filename=gallery.filenames[i],
                    distance=d,
                    similarity=distance_to_similarity(d),
                    is_match=(d <= self.threshold),
                )
            )
        return results
