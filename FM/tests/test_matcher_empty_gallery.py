"""Unit tests for Matcher behavior against an empty gallery.

Validates: Requirements 4.4
"""

import numpy as np

from facial_recognition.matcher import Matcher
from facial_recognition.models import GalleryEncodingSet


def test_find_best_match_returns_none_for_empty_gallery():
    matcher = Matcher()
    empty = GalleryEncodingSet()
    query = np.zeros(128)

    assert matcher.find_best_match(query, empty) is None


def test_rank_returns_empty_list_for_empty_gallery():
    matcher = Matcher()
    empty = GalleryEncodingSet()
    query = np.zeros(128)

    assert matcher.rank(query, empty, top_k=5) == []
