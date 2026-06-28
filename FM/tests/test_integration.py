"""End-to-end integration tests for the facial recognition pipeline.

These tests exercise the full pipeline -- ``EncodingCache`` + ``GalleryManager``
+ ``Encoder``/seam + ``Matcher`` -- end to end, focusing on the two behaviors
called out by Task 10.1:

- **Self-match identity** (Requirement 4.1 / design Property 3): encoding a
  gallery image and matching it against a gallery that contains it returns that
  same file as the best match with ``distance ~ 0`` and ``similarity ~ 1``.
- **Cache consistency** (Requirement 6.1 / design Property 5): running the
  pipeline a second time over the same on-disk cache (the warm-cache path)
  yields identical ``MatchResult``s.

There are two complementary tests:

1. ``test_real_stack_self_match_and_warm_cache`` uses the **real** ``Encoder``
   (native ``face_recognition``/``dlib``). It is guarded with a skip marker so
   it only runs where the native stack is installed; everywhere else it is
   skipped gracefully. Fixture images are copied at test time from the existing
   ``sample/`` gallery into a temp dir, so no binaries are committed.

2. ``test_mock_seam_self_match_and_warm_cache`` exercises the same pipeline
   wiring with a deterministic fake encoder seam over **real** on-disk PNG
   files and a **real** cache. It runs everywhere (no native deps), giving us
   end-to-end coverage of Requirements 4.1 and 6.1 in CI.

Validates: Requirements 4.1, 6.1
"""

from __future__ import annotations

import importlib.util
import os
import shutil

import numpy as np
import pytest
from PIL import Image

from facial_recognition.cache import EncodingCache
from facial_recognition.gallery import GalleryManager
from facial_recognition.matcher import Matcher


# ---------------------------------------------------------------------------
# Native-stack availability guard
# ---------------------------------------------------------------------------
_FACE_RECOGNITION_AVAILABLE = (
    importlib.util.find_spec("face_recognition") is not None
)

# A handful of sample images shipped with the project, used as real fixtures
# for the native-stack end-to-end test.
_SAMPLE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sample"
)


def _copy_sample_fixtures(dest_dir: str, count: int = 3) -> list[str]:
    """Copy up to ``count`` PNG samples into ``dest_dir``.

    Returns the list of destination basenames. Copying at test time avoids
    committing binary fixtures while still exercising the pipeline against real
    portrait images.
    """
    if not os.path.isdir(_SAMPLE_DIR):
        return []
    samples = sorted(
        name for name in os.listdir(_SAMPLE_DIR) if name.lower().endswith(".png")
    )[:count]
    copied: list[str] = []
    for name in samples:
        shutil.copy2(os.path.join(_SAMPLE_DIR, name), os.path.join(dest_dir, name))
        copied.append(name)
    return copied


# ---------------------------------------------------------------------------
# Test 1: REAL native stack (skipped when face_recognition/dlib unavailable)
# ---------------------------------------------------------------------------
@pytest.mark.skipif(
    not _FACE_RECOGNITION_AVAILABLE,
    reason="face_recognition/dlib not installed; real-stack e2e test skipped",
)
def test_real_stack_self_match_and_warm_cache(tmp_path):
    """Full pipeline with the real Encoder: self-match + warm-cache identity.

    Validates: Requirements 4.1, 6.1
    """
    from facial_recognition.encoder import Encoder

    gallery_dir = tmp_path / "gallery"
    gallery_dir.mkdir()
    copied = _copy_sample_fixtures(str(gallery_dir), count=3)
    if not copied:
        pytest.skip("no sample PNG fixtures available to build a gallery")

    encoder = Encoder(model="hog")

    # Pick the first gallery image that actually has a detectable face; use it
    # both as a gallery member and as the self-match query. Skip if none of the
    # chosen samples contain a detectable face.
    query_basename = None
    for name in copied:
        if encoder.encode_image(str(gallery_dir / name)) is not None:
            query_basename = name
            break
    if query_basename is None:
        pytest.skip("no detectable face in the chosen sample fixtures")

    cache_path = str(tmp_path / "encodings.npz")
    matcher = Matcher(threshold=0.6)

    # COLD run: build the gallery from scratch (cache does not exist yet).
    cold_cache = EncodingCache(cache_path)
    gallery_cold = GalleryManager(encoder, cold_cache).load_gallery(
        str(gallery_dir)
    )
    assert len(gallery_cold) >= 1
    assert os.path.exists(cache_path)

    query_encoding = encoder.encode_image(str(gallery_dir / query_basename))
    assert query_encoding is not None

    best_cold = matcher.find_best_match(query_encoding, gallery_cold)
    assert best_cold is not None
    # Self-match identity: the query equals a gallery image, so that file must
    # be the best match with near-zero distance / near-one similarity.
    assert best_cold.filename == query_basename
    assert best_cold.distance == pytest.approx(0.0, abs=1e-6)
    assert best_cold.similarity == pytest.approx(1.0, abs=1e-6)

    # WARM run: fresh cache instance over the same populated path. Results must
    # be identical to the cold run (cache is purely a performance optimization).
    warm_cache = EncodingCache(cache_path)
    gallery_warm = GalleryManager(encoder, warm_cache).load_gallery(
        str(gallery_dir)
    )
    best_warm = matcher.find_best_match(query_encoding, gallery_warm)
    assert best_warm is not None
    assert best_warm.filename == best_cold.filename
    assert best_warm.distance == pytest.approx(best_cold.distance, abs=1e-9)
    assert best_warm.similarity == pytest.approx(best_cold.similarity, abs=1e-9)
    assert best_warm.is_match == best_cold.is_match


# ---------------------------------------------------------------------------
# Test 2: MOCK encoder seam (runs everywhere, no native deps)
# ---------------------------------------------------------------------------
class _DeterministicMockEncoder:
    """Encoder seam returning a fixed embedding per file basename.

    Mirrors the real ``Encoder.encode_image`` interface but keys off the
    basename rather than pixel content, so the same path always yields the same
    deterministic vector. This lets the full GalleryManager/cache/Matcher
    pipeline run end to end without the native stack.
    """

    def __init__(self, embeddings_by_basename: dict[str, np.ndarray]) -> None:
        self._embeddings = embeddings_by_basename
        self.call_count = 0

    def encode_image(self, image_path: str):
        self.call_count += 1
        return self._embeddings[os.path.basename(image_path)]


class _FailingMockEncoder:
    """Encoder seam that fails if invoked; proves the warm cache is reused."""

    def __init__(self) -> None:
        self.call_count = 0

    def encode_image(self, image_path: str):
        self.call_count += 1
        raise AssertionError(
            f"warm-cache encoder should not be called, but was for {image_path!r}"
        )


def test_mock_seam_self_match_and_warm_cache(tmp_path):
    """Full pipeline with a mock encoder seam: self-match + warm-cache identity.

    Builds a real on-disk gallery of PNG files and a real cache, assigns each
    file a distinct deterministic embedding, then uses one gallery file's own
    embedding as the query. The best match must be that same file with
    ``distance ~ 0``; a second (warm-cache) run must reproduce the results.

    Validates: Requirements 4.1, 6.1
    """
    gallery_dir = tmp_path / "gallery"
    gallery_dir.mkdir()

    # Three distinct, well-separated embeddings so the self-match is unambiguous.
    basenames = ["alice.png", "bob.png", "carol.png"]
    embeddings_by_basename: dict[str, np.ndarray] = {}
    for i, name in enumerate(basenames):
        vec = np.zeros(128, dtype=np.float64)
        vec[i] = float(i + 1)  # distinct direction/magnitude per file
        embeddings_by_basename[name] = vec
        # Write a real (tiny) PNG so file signatures are stable on disk.
        Image.new("RGB", (8, 8)).save(str(gallery_dir / name))

    cache_path = str(tmp_path / "encodings.npz")
    matcher = Matcher(threshold=0.6)

    # Self-match query: reuse one gallery file's own deterministic embedding.
    query_basename = "bob.png"
    query_encoding = embeddings_by_basename[query_basename]

    # COLD run: fresh cache; encoder invoked for every gallery image.
    cold_encoder = _DeterministicMockEncoder(embeddings_by_basename)
    cold_cache = EncodingCache(cache_path)
    gallery_cold = GalleryManager(cold_encoder, cold_cache).load_gallery(
        str(gallery_dir)
    )
    assert len(gallery_cold) == len(basenames)
    assert cold_encoder.call_count == len(basenames)
    assert os.path.exists(cache_path)

    best_cold = matcher.find_best_match(query_encoding, gallery_cold)
    assert best_cold is not None
    assert best_cold.filename == query_basename
    assert best_cold.distance == pytest.approx(0.0, abs=1e-9)
    assert best_cold.similarity == pytest.approx(1.0, abs=1e-9)
    assert best_cold.is_match is True

    # WARM run: fresh cache instance over the same populated path. The encoder
    # must never be called (every signature matches) and results must match.
    warm_encoder = _FailingMockEncoder()
    warm_cache = EncodingCache(cache_path)
    gallery_warm = GalleryManager(warm_encoder, warm_cache).load_gallery(
        str(gallery_dir)
    )
    assert warm_encoder.call_count == 0

    best_warm = matcher.find_best_match(query_encoding, gallery_warm)
    assert best_warm is not None
    assert best_warm.filename == best_cold.filename
    assert best_warm.distance == pytest.approx(best_cold.distance, abs=1e-12)
    assert best_warm.similarity == pytest.approx(best_cold.similarity, abs=1e-12)
    assert best_warm.is_match == best_cold.is_match

    # Full top-k results must also be identical between cold and warm runs.
    results_cold = matcher.rank(query_encoding, gallery_cold, top_k=len(basenames))
    results_warm = matcher.rank(query_encoding, gallery_warm, top_k=len(basenames))
    assert len(results_cold) == len(results_warm)
    for cold, warm in zip(results_cold, results_warm):
        assert cold.filename == warm.filename
        assert cold.distance == pytest.approx(warm.distance, abs=1e-12)
        assert cold.similarity == pytest.approx(warm.similarity, abs=1e-12)
        assert cold.is_match == warm.is_match
