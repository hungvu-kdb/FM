"""Property-based tests for :meth:`GalleryManager._list_png_files`.

These tests exercise the gallery PNG enumeration logic across many randomly
generated filename sets using Hypothesis.

Property 10: PNG enumeration case-insensitivity
    For any directory of files with varied extensions and letter cases,
    ``_list_png_files`` selects exactly the files whose name ends in ``.png``
    matched case-insensitively (``name.lower().endswith(".png")``).

Validates: Requirements 3.1
"""

from __future__ import annotations

import os
import shutil
import tempfile
from typing import List

from hypothesis import given, settings
from hypothesis import strategies as st

from facial_recognition.gallery import GalleryManager


# Base name: ASCII letters + digits only. This avoids characters that are
# invalid in Windows filenames (< > : " / \ | ? *) and keeps names portable.
_base_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=(),
        whitelist_characters="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        max_codepoint=126,
    ),
    min_size=1,
    max_size=12,
)

# A mix of extensions covering various-case ``.png`` and non-png suffixes,
# plus the empty string for names with no extension.
_extensions = [
    ".png",
    ".PNG",
    ".Png",
    ".pNg",
    ".txt",
    ".jpg",
    ".jpeg",
    ".PNGX",  # superficially png-like but must NOT match
    ".png.txt",  # ends in .txt -> must NOT match
    "",
]
_ext_strategy = st.sampled_from(_extensions)


@st.composite
def _filename_sets(draw) -> List[str]:
    """Build a list of filenames that are unique case-insensitively.

    Filesystems on Windows are case-insensitive, so two names differing only by
    case would collide on disk. We enforce case-insensitive uniqueness of the
    full filename to keep every generated file distinct.
    """
    pairs = draw(
        st.lists(
            st.tuples(_base_strategy, _ext_strategy),
            min_size=0,
            max_size=15,
        )
    )
    names: List[str] = []
    seen_lower: set[str] = set()
    for base, ext in pairs:
        name = base + ext
        key = name.lower()
        if key in seen_lower:
            continue
        seen_lower.add(key)
        names.append(name)
    return names


@settings(max_examples=100)
@given(names=_filename_sets())
def test_list_png_files_selects_case_insensitive_png_subset(
    names: List[str],
) -> None:
    """_list_png_files returns exactly the case-insensitive ``.png`` subset.

    Validates: Requirements 3.1
    """
    # Hypothesis discourages function-scoped pytest fixtures (e.g. tmp_path),
    # so create and clean up the temp directory inside the test body.
    tmp_dir = tempfile.mkdtemp(prefix="gallery_enum_")
    try:
        for name in names:
            with open(os.path.join(tmp_dir, name), "w", encoding="utf-8"):
                pass

        # _list_png_files does not use encoder/cache, so None is fine here.
        manager = GalleryManager(encoder=None, cache=None)
        selected_paths = manager._list_png_files(tmp_dir)
        selected_basenames = {os.path.basename(p) for p in selected_paths}

        expected = {n for n in names if n.lower().endswith(".png")}

        assert selected_basenames == expected
        # Returned paths must be full paths inside the temp dir.
        for p in selected_paths:
            assert os.path.dirname(p) == tmp_dir
        # Results must be sorted for deterministic ordering.
        assert selected_paths == sorted(selected_paths)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
