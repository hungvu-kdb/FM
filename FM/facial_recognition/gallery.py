"""GalleryManager: build and reconcile the gallery encoding set.

The GalleryManager discovers the gallery images in a directory, reconciles them
against a persisted :class:`~facial_recognition.cache.EncodingCache`, and builds
the in-memory :class:`~facial_recognition.models.GalleryEncodingSet` used for
matching.

Reconciliation rules (see the design's "Gallery loading with cache
reconciliation"):

- Enumerate ``*.png`` files case-insensitively.
- Reuse a cached encoding when the current file signature matches the cached
  one; re-encode when it differs or the file is new.
- Skip (and log a warning for) images with no detectable face.
- Persist a cache that contains exactly the files currently present in the
  gallery, implicitly dropping entries for deleted files.
"""

from __future__ import annotations

import logging
import os
from typing import Dict

import numpy as np

from .cache import EncodingCache
from .encoder import Encoder
from .models import CacheEntry, ENCODING_DIM, GalleryEncodingSet

logger = logging.getLogger(__name__)


class GalleryManager:
    """Build and maintain the set of gallery encodings."""

    def __init__(self, encoder: Encoder, cache: EncodingCache) -> None:
        self.encoder = encoder
        self.cache = cache

    def _list_png_files(self, gallery_dir: str) -> list[str]:
        """Return sorted full paths of ``*.png`` files (case-insensitive).

        Only regular files whose name ends with ``.png`` (matched against the
        lowercased name) are returned. Results are sorted for deterministic
        ordering across runs.
        """
        paths: list[str] = []
        with os.scandir(gallery_dir) as it:
            for entry in it:
                if entry.is_file() and entry.name.lower().endswith(".png"):
                    paths.append(os.path.join(gallery_dir, entry.name))
        paths.sort()
        return paths

    def load_gallery(self, gallery_dir: str) -> GalleryEncodingSet:
        """Discover images, reuse cache, encode new/changed files, persist, build set.

        Args:
            gallery_dir: Directory containing the gallery ``*.png`` images.

        Returns:
            A :class:`GalleryEncodingSet` whose rows correspond exactly to the
            current gallery files that have a detectable face.
        """
        cached = self.cache.load()
        current_paths = self._list_png_files(gallery_dir)
        entries: Dict[str, CacheEntry] = {}

        for path in current_paths:
            size, mtime = self.cache.file_signature(path)
            sig = (size, mtime)
            if path in cached and cached[path].signature == sig:
                # Reuse: file unchanged since it was last encoded.
                entries[path] = cached[path]
            else:
                # New or changed file -> re-encode.
                encoding = self.encoder.encode_image(path)
                if encoding is not None:
                    entries[path] = CacheEntry(
                        image_path=path,
                        size_bytes=size,
                        mtime=mtime,
                        encoding=encoding,
                    )
                else:
                    # No detectable face -> skip and log.
                    logger.warning(
                        "Skipping gallery image with no detectable face: %s",
                        path,
                    )

        # Persisting the reconciled entries drops cache rows for deleted files.
        self.cache.save(entries)

        return self._build_encoding_set(entries)

    @staticmethod
    def _build_encoding_set(entries: Dict[str, CacheEntry]) -> GalleryEncodingSet:
        """Build a :class:`GalleryEncodingSet` from reconciled cache entries.

        ``filenames`` are the basenames of the entry paths and stay parallel to
        the rows of ``matrix``. Ordering follows the insertion order of
        ``entries`` (which is the sorted enumeration order), keeping filenames
        and matrix rows consistent.
        """
        paths = list(entries.keys())
        filenames = [os.path.basename(p) for p in paths]
        if paths:
            matrix = np.stack(
                [np.asarray(entries[p].encoding, dtype=np.float64) for p in paths]
            )
        else:
            matrix = np.empty((0, ENCODING_DIM), dtype=np.float64)
        return GalleryEncodingSet(filenames=filenames, matrix=matrix)
