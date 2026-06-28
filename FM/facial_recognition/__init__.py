"""Facial recognition: 1-to-many facial similarity matching.

This package exposes the public API for the facial recognition tool:

- ``Encoder``        -- detect a face and produce a 128-d embedding.
- ``EncodingCache``  -- persist/retrieve gallery embeddings on disk.
- ``GalleryManager`` -- build and reconcile the gallery encoding set.
- ``Matcher``        -- compare a query embedding against the gallery.

The ``Encoder`` depends on the native ``face_recognition``/``dlib`` stack,
which is imported lazily at instantiation time. This keeps the package
importable (and the pure-logic tests runnable) in environments where those
native dependencies are not installed.
"""

from __future__ import annotations

__all__ = [
    "Encoder",
    "EncodingCache",
    "GalleryManager",
    "Matcher",
    "CacheEntry",
    "GalleryEncodingSet",
    "MatchResult",
]

__version__ = "0.1.0"


def __getattr__(name: str):
    """Lazily resolve the public API symbols.

    Using module ``__getattr__`` (PEP 562) defers importing each submodule
    until the symbol is actually accessed. The ``Encoder`` submodule may pull
    in ``face_recognition``/``dlib`` only when it is used, so importing this
    package never requires the native stack.
    """
    if name == "Encoder":
        from .encoder import Encoder

        return Encoder
    if name == "EncodingCache":
        from .cache import EncodingCache

        return EncodingCache
    if name == "GalleryManager":
        from .gallery import GalleryManager

        return GalleryManager
    if name == "Matcher":
        from .matcher import Matcher

        return Matcher
    if name in ("CacheEntry", "GalleryEncodingSet", "MatchResult"):
        from . import models

        return getattr(models, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(list(globals().keys()) + __all__)
