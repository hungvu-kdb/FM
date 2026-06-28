"""EncodingCache: persist and retrieve gallery embeddings on disk.

The cache stores gallery face encodings keyed by their source image path, plus
a file signature (``size_bytes``, ``mtime``) used to detect stale entries. It is
serialized with :func:`numpy.savez` rather than ``pickle`` so that loading an
untrusted/corrupt cache cannot execute arbitrary code (see the design's
"Security Considerations"). A corrupt or missing cache is treated as empty,
which triggers a transparent rebuild upstream.
"""

from __future__ import annotations

import os
import pickle
import tempfile
import zipfile
from typing import Dict, Tuple

import numpy as np

from .models import CacheEntry, ENCODING_DIM


class EncodingCache:
    """Persist/retrieve gallery encodings to avoid re-encoding each run."""

    def __init__(self, cache_path: str) -> None:
        self.cache_path = cache_path

    @staticmethod
    def file_signature(image_path: str) -> Tuple[int, float]:
        """Return ``(size_bytes, mtime)`` for ``image_path`` via ``os.stat``.

        Used to detect stale cache entries: an entry is fresh only while the
        file's current signature equals the one stored at encode time.
        """
        stat = os.stat(image_path)
        return (stat.st_size, stat.st_mtime)

    def save(self, entries: Dict[str, CacheEntry]) -> None:
        """Atomically write ``entries`` to disk.

        The encodings are stacked into an ``(N, 128)`` matrix and stored
        alongside parallel index arrays (image paths, sizes, mtimes) via
        :func:`numpy.savez`. The write goes to a temporary file in the same
        directory and is then moved into place with :func:`os.replace`, so a
        reader never observes a half-written cache.
        """
        # Build a stable, parallel index from the entries dict.
        paths = list(entries.keys())
        if paths:
            sizes = np.array(
                [entries[p].size_bytes for p in paths], dtype=np.int64
            )
            mtimes = np.array(
                [entries[p].mtime for p in paths], dtype=np.float64
            )
            matrix = np.stack(
                [np.asarray(entries[p].encoding, dtype=np.float64) for p in paths]
            )
        else:
            # Empty cache: keep array shapes consistent so load can round-trip.
            sizes = np.empty((0,), dtype=np.int64)
            mtimes = np.empty((0,), dtype=np.float64)
            matrix = np.empty((0, ENCODING_DIM), dtype=np.float64)

        image_paths = np.array(paths, dtype=object)

        cache_dir = os.path.dirname(os.path.abspath(self.cache_path))
        os.makedirs(cache_dir, exist_ok=True)

        # Write to a temp file in the same directory, then atomically replace.
        fd, tmp_path = tempfile.mkstemp(suffix=".tmp", dir=cache_dir)
        try:
            with os.fdopen(fd, "wb") as fh:
                np.savez(
                    fh,
                    image_paths=image_paths,
                    sizes=sizes,
                    mtimes=mtimes,
                    matrix=matrix,
                )
            os.replace(tmp_path, self.cache_path)
        except BaseException:
            # Clean up the temp file if anything went wrong before replace.
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            raise

    def load(self) -> Dict[str, CacheEntry]:
        """Load the cache file into a ``{path: CacheEntry}`` dict.

        Returns an empty dict when the file is missing or corrupt. Any decode or
        schema error (e.g. :class:`zipfile.BadZipFile`, ``KeyError`` for missing
        arrays, ``ValueError`` for malformed data) is swallowed and treated as an
        empty cache so the caller can rebuild safely.
        """
        if not os.path.exists(self.cache_path):
            return {}

        try:
            with np.load(self.cache_path, allow_pickle=True) as data:
                image_paths = data["image_paths"]
                sizes = data["sizes"]
                mtimes = data["mtimes"]
                matrix = data["matrix"]

                n = len(image_paths)
                if not (len(sizes) == len(mtimes) == matrix.shape[0] == n):
                    return {}

                entries: Dict[str, CacheEntry] = {}
                for i in range(n):
                    path = str(image_paths[i])
                    encoding = np.asarray(matrix[i], dtype=np.float64)
                    entries[path] = CacheEntry(
                        image_path=path,
                        size_bytes=int(sizes[i]),
                        mtime=float(mtimes[i]),
                        encoding=encoding,
                    )
                return entries
        except (
            zipfile.BadZipFile,
            pickle.UnpicklingError,
            KeyError,
            ValueError,
            TypeError,
            EOFError,
            OSError,
        ):
            # Corrupt / unreadable / schema-mismatched cache -> rebuild from scratch.
            return {}
