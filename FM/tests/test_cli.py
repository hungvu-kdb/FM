"""Unit tests for CLI exit codes and output.

These tests exercise :func:`facial_recognition.cli.main` without the native
``face_recognition``/``dlib`` stack. The pipeline pieces are mocked by patching
the source module attributes that ``cli.main`` imports at call time
(``from .module import Name``), so the patched objects are bound on import.

Validates: Requirements 5.1, 5.2, 5.4, 5.5, 5.6
"""

import numpy as np
import pytest

from facial_recognition.cli import main
from facial_recognition.models import GalleryEncodingSet, MatchResult


# ---------------------------------------------------------------------------
# Fakes for the deferred pipeline imports in cli.main
# ---------------------------------------------------------------------------
class _FakeEncodingCache:
    """No-op stand-in for EncodingCache accepting a cache path."""

    def __init__(self, cache_path):
        self.cache_path = cache_path


class _FakeEncoder:
    """Stand-in for Encoder; encode_image returns a configurable value."""

    encode_return = None

    def __init__(self, model="hog"):
        self.model = model

    def encode_image(self, path):
        return type(self).encode_return


class _FakeGalleryManager:
    """Stand-in for GalleryManager; load_gallery returns a configured set."""

    gallery_return = None

    def __init__(self, encoder, cache):
        self.encoder = encoder
        self.cache = cache

    def load_gallery(self, gallery_dir):
        return type(self).gallery_return


class _FakeMatcher:
    """Stand-in for Matcher; rank returns configured results honoring top_k."""

    rank_return = []

    def __init__(self, threshold=0.6):
        self.threshold = threshold

    def rank(self, query_encoding, gallery, top_k):
        if top_k == 0:
            return []
        return type(self).rank_return[:top_k]


def _empty_gallery():
    return GalleryEncodingSet()


def _nonempty_gallery():
    return GalleryEncodingSet(filenames=["x.png"], matrix=np.zeros((1, 128)))


def _patch_pipeline(monkeypatch):
    """Patch the source-module attributes that cli.main imports at call time."""
    monkeypatch.setattr(
        "facial_recognition.cache.EncodingCache", _FakeEncodingCache
    )
    monkeypatch.setattr("facial_recognition.encoder.Encoder", _FakeEncoder)
    monkeypatch.setattr(
        "facial_recognition.gallery.GalleryManager", _FakeGalleryManager
    )
    monkeypatch.setattr("facial_recognition.matcher.Matcher", _FakeMatcher)


# ---------------------------------------------------------------------------
# Exit 1: invalid/missing query or gallery (Req 5.4)
# ---------------------------------------------------------------------------
def test_missing_query_returns_exit_1(tmp_path, capsys):
    # gallery is a real existing dir so only the query is missing
    missing_query = str(tmp_path / "nonexistent.png")
    code = main([missing_query, "--gallery", str(tmp_path)])

    assert code == 1
    err = capsys.readouterr().err
    assert "query" in err.lower()
    assert missing_query in err


def test_missing_gallery_returns_exit_1(tmp_path, capsys):
    # query is a real file; gallery points at a directory that does not exist
    query_file = tmp_path / "query.png"
    query_file.write_bytes(b"not really a png")
    missing_gallery = str(tmp_path / "no_such_dir")

    code = main([str(query_file), "--gallery", missing_gallery])

    assert code == 1
    err = capsys.readouterr().err
    assert "gallery" in err.lower()
    assert missing_gallery in err


# ---------------------------------------------------------------------------
# Exit 3: no encodable faces in the gallery (Req 5.6)
# ---------------------------------------------------------------------------
def test_empty_gallery_returns_exit_3(tmp_path, capsys, monkeypatch):
    _patch_pipeline(monkeypatch)
    _FakeGalleryManager.gallery_return = _empty_gallery()

    query_file = tmp_path / "query.png"
    query_file.write_bytes(b"data")

    code = main([str(query_file), "--gallery", str(tmp_path)])

    assert code == 3
    err = capsys.readouterr().err
    assert "No encodable faces found in gallery" in err


# ---------------------------------------------------------------------------
# Exit 2: no face detected in the query image (Req 5.5)
# ---------------------------------------------------------------------------
def test_no_query_face_returns_exit_2(tmp_path, capsys, monkeypatch):
    _patch_pipeline(monkeypatch)
    _FakeGalleryManager.gallery_return = _nonempty_gallery()
    _FakeEncoder.encode_return = None  # query has no detectable face

    query_file = tmp_path / "query.png"
    query_file.write_bytes(b"data")

    code = main([str(query_file), "--gallery", str(tmp_path)])

    assert code == 2
    err = capsys.readouterr().err
    assert "No face detected in query image" in err


# ---------------------------------------------------------------------------
# Success + output (Req 5.1)
# ---------------------------------------------------------------------------
def test_valid_run_prints_filename_similarity_distance(
    tmp_path, capsys, monkeypatch
):
    _patch_pipeline(monkeypatch)
    _FakeGalleryManager.gallery_return = _nonempty_gallery()
    _FakeEncoder.encode_return = np.zeros(128)
    _FakeMatcher.rank_return = [
        MatchResult(
            filename="100013.png",
            distance=0.219,
            similarity=0.820,
            is_match=True,
        )
    ]

    query_file = tmp_path / "query.png"
    query_file.write_bytes(b"data")

    code = main([str(query_file), "--gallery", str(tmp_path)])

    assert code == 0
    out = capsys.readouterr().out
    assert "100013.png" in out
    assert "similarity" in out
    assert "distance" in out


# ---------------------------------------------------------------------------
# top-k 0 prints no match lines (Req 5.2)
# ---------------------------------------------------------------------------
def test_top_k_zero_prints_no_match_lines(tmp_path, capsys, monkeypatch):
    _patch_pipeline(monkeypatch)
    _FakeGalleryManager.gallery_return = _nonempty_gallery()
    _FakeEncoder.encode_return = np.zeros(128)
    _FakeMatcher.rank_return = [
        MatchResult(
            filename="100013.png",
            distance=0.219,
            similarity=0.820,
            is_match=True,
        )
    ]

    query_file = tmp_path / "query.png"
    query_file.write_bytes(b"data")

    code = main([str(query_file), "--gallery", str(tmp_path), "--top-k", "0"])

    assert code == 0
    out = capsys.readouterr().out
    assert "Best match" not in out
    assert "100013.png" not in out
    assert out.strip() == ""
