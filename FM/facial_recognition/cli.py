"""CLI: command-line orchestration and output.

This module parses command-line arguments, validates the input paths, wires the
pipeline components (:class:`~facial_recognition.encoder.Encoder`,
:class:`~facial_recognition.cache.EncodingCache`,
:class:`~facial_recognition.gallery.GalleryManager`,
:class:`~facial_recognition.matcher.Matcher`), runs a 1-to-many match, prints
the result, and maps error conditions to exit codes.

Exit codes (see the design's "Error Handling" and Requirement 5):

- ``0`` -- success.
- ``1`` -- invalid/missing query file or gallery directory (Req 5.4).
- ``2`` -- no face detected in the query image (Req 5.5).
- ``3`` -- no encodable faces found in the gallery (Req 5.6).

The ``Encoder`` defers importing the native ``face_recognition``/``dlib`` stack
until it is actually used, so importing this module (and running argument
parsing / path validation) never requires the native dependencies.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import List

# Default gallery directory for the project's sample portrait set.
DEFAULT_GALLERY = r"d:\Mini-Project\FM\sample"

# Cache filename written alongside the gallery directory.
CACHE_FILENAME = ".encodings.npz"

# Exit codes mapped to the error conditions in Requirement 5.
EXIT_OK = 0
EXIT_BAD_PATH = 1
EXIT_NO_QUERY_FACE = 2
EXIT_NO_GALLERY_FACES = 3


def _build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the CLI.

    Positional:
        query: Path to the query image.

    Options:
        --gallery: Gallery directory (default: the project's sample folder).
        --threshold: Max distance to be considered the same person (default 0.6).
        --top-k: Number of ranked matches to print (default 5).
        --model: Detector model, ``hog`` (default) or ``cnn``.
    """
    parser = argparse.ArgumentParser(
        prog="facial_recognition",
        description="Find the gallery face most similar to a query image.",
    )
    parser.add_argument("query", help="Path to the query image (PNG).")
    parser.add_argument(
        "--gallery",
        default=DEFAULT_GALLERY,
        help="Directory of gallery PNG images to search (default: %(default)s).",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.6,
        help="Max distance for two faces to count as the same person "
        "(default: %(default)s).",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        dest="top_k",
        help="Number of ranked matches to print; 0 prints none "
        "(default: %(default)s).",
    )
    parser.add_argument(
        "--model",
        choices=("hog", "cnn"),
        default="hog",
        help="Face detector model: 'hog' (fast, CPU) or 'cnn' (accurate, "
        "slower/GPU) (default: %(default)s).",
    )
    return parser


def _format_match_line(label: str, result) -> str:
    """Format a single match result as a human-readable line.

    Example: ``Best match: 100013.png  (similarity 0.820, distance 0.219, same-person: yes)``.
    """
    same_person = "yes" if result.is_match else "no"
    return (
        f"{label}: {result.filename}  "
        f"(similarity {result.similarity:.3f}, "
        f"distance {result.distance:.3f}, "
        f"same-person: {same_person})"
    )


def main(argv: List[str]) -> int:
    """Parse args, run the pipeline, print results, and return an exit code.

    Args:
        argv: Argument list (excluding the program name), e.g. ``sys.argv[1:]``.

    Returns:
        A process exit code (see the module docstring for the mapping).
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    query_path = args.query
    gallery_dir = args.gallery

    # --- Path validation (Req 5.4): missing query or gallery -> exit 1. ---
    if not os.path.isfile(query_path):
        print(
            f"error: query image does not exist: {query_path}",
            file=sys.stderr,
        )
        return EXIT_BAD_PATH
    if not os.path.isdir(gallery_dir):
        print(
            f"error: gallery directory does not exist: {gallery_dir}",
            file=sys.stderr,
        )
        return EXIT_BAD_PATH

    # Import here so path validation above stays free of the native stack and
    # to keep module import cheap. The Encoder itself further defers the
    # face_recognition/dlib import until detection actually runs.
    from .cache import EncodingCache
    from .encoder import Encoder, ImageDecodeError
    from .gallery import GalleryManager
    from .matcher import Matcher

    # Cache lives alongside the gallery so derived biometric data stays with it.
    cache_path = os.path.join(gallery_dir, CACHE_FILENAME)

    # --- Wire the pipeline (design "Main matching algorithm"). ---
    encoder = Encoder(model=args.model)
    cache = EncodingCache(cache_path)
    gallery = GalleryManager(encoder, cache).load_gallery(gallery_dir)

    # No encodable faces in the gallery (Req 5.6) -> exit 3.
    if len(gallery) == 0:
        print("No encodable faces found in gallery", file=sys.stderr)
        return EXIT_NO_GALLERY_FACES

    # Encode the query face. A successful decode with no face yields None;
    # an undecodable query image is also treated as unusable (no face) since
    # the query cannot be matched either way (Req 5.5) -> exit 2.
    try:
        query_encoding = encoder.encode_image(query_path)
    except ImageDecodeError:
        query_encoding = None
    if query_encoding is None:
        print("No face detected in query image", file=sys.stderr)
        return EXIT_NO_QUERY_FACE

    # --- Rank and print (Req 5.1, 5.2). ---
    # Behavior for top_k:
    #   - top_k == 0: no ranked results were requested, so print no match
    #     lines at all (Req 5.2) and return success.
    #   - top_k >= 1: print the best match (results[0], Req 5.1); when
    #     top_k > 1 also print the remaining ranked lines.
    matcher = Matcher(threshold=args.threshold)
    results = matcher.rank(query_encoding, gallery, top_k=args.top_k)

    if results:
        print(_format_match_line("Best match", results[0]))
        for rank_index, result in enumerate(results[1:], start=2):
            print(_format_match_line(f"  #{rank_index}", result))

    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
