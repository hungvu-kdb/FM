"""Encoder: detect a face and produce a 128-d embedding.

The Encoder loads an image from disk, normalizes it to RGB, locates faces
using the configured detector model ("hog" or "cnn"), and produces a
128-dimensional embedding for each detected face.

The native ``face_recognition``/``dlib`` stack is imported lazily inside the
detector seam (:meth:`Encoder._detect_and_encode`) rather than at module load
time. This keeps the module importable in environments where the native
dependencies are not installed, and lets tests monkeypatch the seam without
needing the native stack.
"""

from __future__ import annotations

from typing import List, Optional

import numpy as np


class ImageDecodeError(Exception):
    """Raised when image bytes cannot be decoded into an RGB array.

    This is a catchable, typed error so callers can signal a decoding failure
    without crashing the System (see Requirement 1.3).
    """


class Encoder:
    """Detect a face in an image and convert it to a 128-d embedding."""

    def __init__(self, model: str = "hog", num_jitters: int = 1) -> None:
        """Create an Encoder.

        Args:
            model: Detector model used to locate faces. Either ``"hog"``
                (fast, CPU) or ``"cnn"`` (accurate, slower/GPU).
            num_jitters: How many times to re-sample each face when computing
                its encoding. Higher values are slower but slightly more
                accurate.
        """
        self.model = model
        self.num_jitters = num_jitters

    # ------------------------------------------------------------------
    # Image loading
    # ------------------------------------------------------------------
    def _load_rgb(self, image_path: str) -> np.ndarray:
        """Load ``image_path`` and normalize it to an RGB numpy array.

        Uses Pillow to open and convert the image to 3-channel RGB, then
        returns it as a ``numpy.ndarray`` of shape ``(H, W, 3)``.

        Raises:
            ImageDecodeError: if the bytes cannot be decoded as an image.
        """
        # Deferred import: Pillow is a light dependency, but keep the import
        # local so the seam stays self-contained and easy to reason about.
        from PIL import Image, UnidentifiedImageError

        try:
            with Image.open(image_path) as img:
                rgb = img.convert("RGB")
                return np.asarray(rgb)
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise ImageDecodeError(
                f"could not decode image bytes from {image_path!r}: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Detector seam (mocked in tests)
    # ------------------------------------------------------------------
    def _detect_and_encode(self, rgb_image: np.ndarray) -> List[np.ndarray]:
        """Locate faces in ``rgb_image`` and return one encoding per face.

        This method is the seam between the Encoder and the native
        ``face_recognition``/``dlib`` stack. The import is deferred to runtime
        so the module stays importable without the native dependencies, and
        tests can monkeypatch this method to supply deterministic encodings.

        The configured detector ``model`` ("hog"/"cnn") is passed through to
        ``face_recognition.face_locations`` (Requirement 1.5).

        Args:
            rgb_image: RGB image array of shape ``(H, W, 3)``.

        Returns:
            A list of 128-d embeddings, one per detected face (possibly empty).
        """
        import face_recognition

        locations = face_recognition.face_locations(rgb_image, model=self.model)
        if not locations:
            return []
        encodings = face_recognition.face_encodings(
            rgb_image,
            known_face_locations=locations,
            num_jitters=self.num_jitters,
        )
        return list(encodings)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def encode_image(self, image_path: str) -> Optional[np.ndarray]:
        """Return the 128-d embedding for the most prominent face.

        Loads and normalizes the image, then detects and encodes faces. When
        detection succeeds but finds no faces, returns ``None`` rather than
        raising (Requirement 1.2). When the image bytes cannot be decoded,
        :class:`ImageDecodeError` is raised (Requirement 1.3).

        "Most prominent" is taken to be the first face returned by the detector
        seam; the underlying ``face_recognition`` library returns faces in a
        stable order, so the first encoding is used for simplicity.

        Args:
            image_path: Path to the image file.

        Returns:
            A ``(128,)`` ``numpy.ndarray`` for the most prominent face, or
            ``None`` if no face is detected.

        Raises:
            ImageDecodeError: if the image bytes cannot be decoded.
        """
        rgb_image = self._load_rgb(image_path)
        encodings = self._detect_and_encode(rgb_image)
        if not encodings:
            return None
        return encodings[0]

    def encode_all_faces(self, image_path: str) -> List[np.ndarray]:
        """Return one 128-d embedding for every detected face.

        Loads and normalizes the image, then detects and encodes every face,
        honoring the configured detector ``model`` (Requirement 1.4, 1.5).

        Args:
            image_path: Path to the image file.

        Returns:
            A list of ``(128,)`` ``numpy.ndarray`` embeddings, one per detected
            face. The list is empty when no faces are detected.

        Raises:
            ImageDecodeError: if the image bytes cannot be decoded.
        """
        rgb_image = self._load_rgb(image_path)
        return self._detect_and_encode(rgb_image)
