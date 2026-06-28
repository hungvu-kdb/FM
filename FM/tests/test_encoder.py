"""Unit tests for :class:`facial_recognition.encoder.Encoder` using a mocked detector.

The native ``face_recognition``/``dlib`` stack is NOT installed in this
environment, so these tests never call the real detector. Instead they
monkeypatch the detector seam (:meth:`Encoder._detect_and_encode`) and/or inject
a fake ``face_recognition`` module into ``sys.modules`` to exercise the
model pass-through behavior. Image loading is either monkeypatched
(:meth:`Encoder._load_rgb`) or driven with real bytes via Pillow (installed).

Validates: Requirements 1.2, 1.3, 1.4, 1.5
"""

from __future__ import annotations

import sys
import types

import numpy as np
import pytest

from facial_recognition.encoder import Encoder, ImageDecodeError
from facial_recognition.models import ENCODING_DIM


def _dummy_rgb() -> np.ndarray:
    """A small RGB array standing in for a decoded image."""
    return np.zeros((10, 10, 3), dtype=np.uint8)


# ----------------------------------------------------------------------
# Requirement 1.2: zero faces -> None, no raise
# ----------------------------------------------------------------------
def test_encode_image_returns_none_for_zero_faces(monkeypatch) -> None:
    """encode_image returns None (no raise) when detection finds no faces.

    Validates: Requirements 1.2
    """
    encoder = Encoder(model="hog")
    monkeypatch.setattr(encoder, "_load_rgb", lambda path: _dummy_rgb())
    monkeypatch.setattr(encoder, "_detect_and_encode", lambda rgb: [])

    result = encoder.encode_image("anything.png")

    assert result is None


# ----------------------------------------------------------------------
# Requirement 1.1/1.4: one face -> a (128,) embedding
# ----------------------------------------------------------------------
def test_encode_image_returns_128d_for_single_face(monkeypatch) -> None:
    """encode_image returns the first (128,) embedding when one face is found.

    Validates: Requirements 1.1, 1.4
    """
    encoder = Encoder(model="hog")
    embedding = np.arange(ENCODING_DIM, dtype=np.float64)
    monkeypatch.setattr(encoder, "_load_rgb", lambda path: _dummy_rgb())
    monkeypatch.setattr(encoder, "_detect_and_encode", lambda rgb: [embedding])

    result = encoder.encode_image("face.png")

    assert result is not None
    assert isinstance(result, np.ndarray)
    assert result.shape == (ENCODING_DIM,)
    np.testing.assert_array_equal(result, embedding)


# ----------------------------------------------------------------------
# Requirement 1.4: multiple faces -> list of embeddings
# ----------------------------------------------------------------------
def test_encode_all_faces_returns_list_for_multiple_faces(monkeypatch) -> None:
    """encode_all_faces returns one (128,) embedding per detected face.

    Validates: Requirements 1.4
    """
    encoder = Encoder(model="hog")
    embeddings = [
        np.full(ENCODING_DIM, i, dtype=np.float64) for i in range(3)
    ]
    monkeypatch.setattr(encoder, "_load_rgb", lambda path: _dummy_rgb())
    monkeypatch.setattr(encoder, "_detect_and_encode", lambda rgb: list(embeddings))

    results = encoder.encode_all_faces("group.png")

    assert isinstance(results, list)
    assert len(results) == 3
    for got, expected in zip(results, embeddings):
        assert got.shape == (ENCODING_DIM,)
        np.testing.assert_array_equal(got, expected)


def test_encode_image_returns_first_of_multiple_faces(monkeypatch) -> None:
    """encode_image returns the most prominent (first) face when several exist.

    Validates: Requirements 1.1, 1.4
    """
    encoder = Encoder(model="hog")
    first = np.full(ENCODING_DIM, 7.0, dtype=np.float64)
    second = np.full(ENCODING_DIM, 9.0, dtype=np.float64)
    monkeypatch.setattr(encoder, "_load_rgb", lambda path: _dummy_rgb())
    monkeypatch.setattr(encoder, "_detect_and_encode", lambda rgb: [first, second])

    result = encoder.encode_image("group.png")

    np.testing.assert_array_equal(result, first)


# ----------------------------------------------------------------------
# Requirement 1.3: undecodable bytes -> ImageDecodeError (handled failure)
# ----------------------------------------------------------------------
def test_encode_image_raises_imagedecodeerror_for_undecodable_bytes(tmp_path) -> None:
    """Undecodable image bytes surface as ImageDecodeError, not a crash.

    Uses the REAL _load_rgb path (Pillow is installed) against garbage bytes
    written with a .png extension.

    Validates: Requirements 1.3
    """
    bad_path = tmp_path / "garbage.png"
    bad_path.write_bytes(b"this is definitely not a valid PNG file \x00\xff\x01\x02")

    encoder = Encoder(model="hog")

    with pytest.raises(ImageDecodeError):
        encoder.encode_image(str(bad_path))


# ----------------------------------------------------------------------
# Requirement 1.5: configured model is passed through to the detector
# ----------------------------------------------------------------------
@pytest.mark.parametrize("model", ["hog", "cnn"])
def test_configured_model_passed_to_detector(monkeypatch, model) -> None:
    """The Encoder forwards its configured model to face_recognition.face_locations.

    A fake ``face_recognition`` module is injected into sys.modules so the
    lazily-imported detector seam records the model argument without touching
    the native stack.

    Validates: Requirements 1.5
    """
    recorded = {}

    fake_module = types.ModuleType("face_recognition")

    def fake_face_locations(rgb_image, model=None):
        recorded["model"] = model
        # Return a non-empty list so face_encodings is invoked.
        return [(0, 1, 2, 3)]

    def fake_face_encodings(rgb_image, known_face_locations=None, num_jitters=1):
        return [np.zeros(ENCODING_DIM, dtype=np.float64)]

    fake_module.face_locations = fake_face_locations
    fake_module.face_encodings = fake_face_encodings
    monkeypatch.setitem(sys.modules, "face_recognition", fake_module)

    encoder = Encoder(model=model)
    monkeypatch.setattr(encoder, "_load_rgb", lambda path: _dummy_rgb())

    result = encoder.encode_image("face.png")

    assert recorded["model"] == model
    assert result is not None
    assert result.shape == (ENCODING_DIM,)
