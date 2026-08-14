"""Football Manager portrait frame — all three MVPs as plain functions.

Usage:
    from convert import mvp1, mvp2, mvp3

    mvp1("input.png", "test/output.png")
    mvp2("input.png", "test/output.png")
    mvp3("input.png", "test/output.png")

Every function takes an input path and an output path, writes a 260x310 RGBA
PNG, and returns the output path. Off-size input is resized automatically and
the output directory is created if it does not exist.

The three approaches, all fitted from the 46 samples in Root/:

    mvp1  dense per-pixel alpha template      (MVP1/template_alpha.npy)
    mvp2  procedural rounded-rect SDF + halo  (MVP2/model.json, 13 scalars)
    mvp3  rank-8 separable factorization      (MVP3/model.json, 1-D profiles)

Each function is byte-for-byte identical to the standalone implementation it
replaces (MVP1/apply_border.py, MVP2/apply_frame.py, MVP3/apply-frame.mjs).
MVP3 is a Python port of the Node.js renderer; the model files themselves are
read as-is and are not duplicated here.

Optional keyword arguments are available on each (fit=, model=, ...), but the
defaults are what you want for normal use. See the docstrings below.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np
from PIL import Image

__all__ = ["mvp1", "mvp2", "mvp3", "TARGET_SIZE"]

HERE = Path(__file__).resolve().parent

#: Canonical FM portrait size, (width, height).
TARGET_SIZE = (260, 310)

MVP1_TEMPLATE = HERE / "MVP1" / "template_alpha.npy"
MVP2_MODEL = HERE / "MVP2" / "model.json"
MVP3_MODEL = HERE / "MVP3" / "model.json"

MVP2_KEYS = (
    "width", "height", "center_x", "center_y", "half_width", "half_height",
    "corner_radius", "edge_softness", "content_alpha", "alpha_floor",
    "halo_gap", "halo_sigma", "halo_peak",
)

#: Frame alpha at or above this level is treated as portrait content (MVP3).
MVP3_CONTENT_THRESHOLD = 128

_CACHE: dict[str, Any] = {}


# --------------------------------------------------------------------------- #
# shared helpers
# --------------------------------------------------------------------------- #

def _load_rgba(path: str | Path) -> Image.Image:
    with Image.open(path) as image:
        return image.convert("RGBA")


def _resize_exact(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    if image.size == size:
        return image
    return image.resize(size, Image.Resampling.LANCZOS)


def _cover_crop(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Scale to cover the target, then centre-crop, so nothing is letterboxed."""
    target_w, target_h = size
    src_w, src_h = image.size
    scale = max(target_w / src_w, target_h / src_h)
    scaled = image.resize(
        (max(1, round(src_w * scale)), max(1, round(src_h * scale))),
        Image.Resampling.LANCZOS,
    )
    left = (scaled.size[0] - target_w) // 2
    top = (scaled.size[1] - target_h) // 2
    return scaled.crop((left, top, left + target_w, top + target_h))


def _prepare(path: str | Path, size: tuple[int, int], fit: bool) -> np.ndarray:
    """Load an image and bring it to exactly `size` as a straight RGBA array."""
    image = _load_rgba(path)
    image = _cover_crop(image, size) if fit else _resize_exact(image, size)
    return np.asarray(image, dtype=np.uint8)


def _save(rgba: np.ndarray, output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, mode="RGBA").save(output, format="PNG")
    return output


def _compose(source: np.ndarray, frame_alpha: np.ndarray, content_mask: np.ndarray,
             out_alpha: np.ndarray) -> np.ndarray:
    """Keep source RGB inside the content region, black elsewhere (the glow)."""
    rgb = np.zeros_like(source[..., :3])
    rgb[content_mask] = source[..., :3][content_mask]
    alpha = np.rint(np.clip(out_alpha, 0.0, 255.0)).astype(np.uint8)
    return np.dstack((rgb, alpha))


# --------------------------------------------------------------------------- #
# MVP1 — dense per-pixel alpha template
# --------------------------------------------------------------------------- #

def _mvp1_template(path: Path) -> np.ndarray:
    key = f"mvp1:{path}"
    if key not in _CACHE:
        if not path.exists():
            raise FileNotFoundError(
                f"MVP1 template not found: {path}. Run MVP1/build_template.py first."
            )
        _CACHE[key] = np.load(path)
    return _CACHE[key]


def mvp1(input_path: str | Path, output_path: str | Path, *, fit: bool = False,
         template: str | Path | None = None) -> Path:
    """Apply the MVP1 frame: a dense alpha template measured from the samples.

    The alpha channel is copied verbatim from `template_alpha.npy`, so this is
    the most faithful reproduction of the original artwork (median per-sample
    MAE 0.3326). It is locked to 260x310 and has no tunable parameters.

    Args:
        input_path: any image Pillow can read.
        output_path: destination PNG; parent folders are created.
        fit: scale-to-cover and centre-crop instead of stretching to 260x310.
             Use this when the input aspect ratio differs a lot from 260:310.
        template: override the .npy template path.

    Returns:
        The output path.
    """
    alpha_template = _mvp1_template(Path(template) if template else MVP1_TEMPLATE)
    height, width = alpha_template.shape
    content_mask = alpha_template == 255

    source = _prepare(input_path, (width, height), fit)
    # MVP1 overwrites alpha with the template rather than multiplying, which is
    # what makes it idempotent.
    return _save(
        _compose(source, alpha_template, content_mask,
                 alpha_template.astype(np.float64)),
        output_path,
    )


# --------------------------------------------------------------------------- #
# MVP2 — procedural rounded-rectangle SDF + detached Gaussian halo
# --------------------------------------------------------------------------- #

def _mvp2_model(path: Path) -> Mapping[str, float]:
    key = f"mvp2:{path}"
    if key not in _CACHE:
        if not path.exists():
            raise FileNotFoundError(f"MVP2 model not found: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        missing = [k for k in MVP2_KEYS if k not in data]
        if missing:
            raise ValueError(f"MVP2 model is missing scalars: {', '.join(missing)}")
        for k in MVP2_KEYS:
            if isinstance(data[k], (dict, list)) or not isinstance(data[k], (int, float)):
                raise ValueError(f"MVP2 parameter {k!r} must be a scalar")
        _CACHE[key] = data
    return _CACHE[key]


def _rounded_rect_sdf(width: int, height: int, model: Mapping[str, float]) -> np.ndarray:
    """Signed distance at pixel centres; negative inside, zero on the boundary."""
    y, x = np.mgrid[0:height, 0:width].astype(np.float64)
    radius = float(model["corner_radius"])
    qx = np.abs(x - float(model["center_x"])) - (float(model["half_width"]) - radius)
    qy = np.abs(y - float(model["center_y"])) - (float(model["half_height"]) - radius)
    outside = np.hypot(np.maximum(qx, 0.0), np.maximum(qy, 0.0))
    inside = np.minimum(np.maximum(qx, qy), 0.0)
    return outside + inside - radius


def mvp2(input_path: str | Path, output_path: str | Path, *, fit: bool = False,
         model: str | Path | None = None) -> Path:
    """Apply the MVP2 frame: 13 scalars, rendered analytically.

    The content region is a rounded-rectangle signed distance field with an
    analytical antialiased edge; the glow is a Gaussian in distance, gated to
    fire only outside a 9 px gap. Least accurate of the three (median MAE
    1.4370) but the only genuinely resolution-independent model, and every
    parameter is hand-editable in MVP2/model.json.

    Note: unlike mvp1 and mvp3, this is not perfectly idempotent. Content alpha
    is multiplied by the source alpha, so re-framing an already-framed image
    attenuates the ~28 antialiased edge pixels a second time (0.035% of the
    frame, max delta 63). This matches MVP2/apply_frame.py exactly and is
    preserved here deliberately; feed it an original portrait, not an output.

    Args:
        input_path: any image Pillow can read.
        output_path: destination PNG; parent folders are created.
        fit: scale-to-cover and centre-crop instead of stretching.
        model: override the model JSON path.

    Returns:
        The output path.
    """
    params = _mvp2_model(Path(model) if model else MVP2_MODEL)
    width, height = int(params["width"]), int(params["height"])
    source = _prepare(input_path, (width, height), fit)

    sdf = _rounded_rect_sdf(width, height, params)
    softness = max(float(params["edge_softness"]), 1e-6)
    coverage = np.clip(0.5 - sdf / softness, 0.0, 1.0)

    # Content honours the source's own transparency.
    content = float(params["content_alpha"]) * coverage
    content *= source[..., 3].astype(np.float64) / 255.0

    floor = float(params["alpha_floor"])
    halo = np.full((height, width), floor, dtype=np.float64)
    gap = float(params["halo_gap"])
    exterior = sdf >= gap
    z = (sdf[exterior] - gap) / max(float(params["halo_sigma"]), 1e-6)
    halo[exterior] = floor + (float(params["halo_peak"]) - floor) * np.exp(-0.5 * z * z)

    out_alpha = np.maximum(content, halo)
    return _save(_compose(source, out_alpha, coverage > 0.0, out_alpha), output_path)


# --------------------------------------------------------------------------- #
# MVP3 — rank-8 separable factorization
# --------------------------------------------------------------------------- #

def _mvp3_frame(path: Path) -> np.ndarray:
    """Rebuild the frame from 1-D profiles: A(y,x) = sum_k s_k u_k(y) v_k(x)."""
    key = f"mvp3:{path}"
    if key not in _CACHE:
        if not path.exists():
            raise FileNotFoundError(f"MVP3 model not found: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        width, height = int(data["width"]), int(data["height"])
        terms = data.get("terms")
        if not terms:
            raise ValueError("MVP3 model has no separable terms")

        alpha = np.zeros((height, width), dtype=np.float64)
        for term in terms:
            rows = np.asarray(term["rows"], dtype=np.float64)
            cols = np.asarray(term["cols"], dtype=np.float64)
            if rows.shape != (height,) or cols.shape != (width,):
                raise ValueError("MVP3 term profile lengths do not match the model size")
            alpha += float(term["weight"]) * np.outer(rows, cols)
        _CACHE[key] = np.clip(alpha, 0.0, 255.0)
    return _CACHE[key]


def mvp3(input_path: str | Path, output_path: str | Path, *, fit: bool = False,
         model: str | Path | None = None) -> Path:
    """Apply the MVP3 frame: a rank-8 separable factorization of the alpha field.

    The frame is stored as 1-D row and column profiles and rebuilt at call time
    (4,568 numbers, 5.7% of a dense matrix), yet lands within noise of MVP1 at
    median MAE 0.3470. Source alpha is normalised against the frame before
    re-applying, which makes the operation exactly idempotent.

    Args:
        input_path: any image Pillow can read.
        output_path: destination PNG; parent folders are created.
        fit: scale-to-cover and centre-crop instead of stretching.
        model: override the model JSON path.

    Returns:
        The output path.
    """
    frame = _mvp3_frame(Path(model) if model else MVP3_MODEL)
    height, width = frame.shape
    source = _prepare(input_path, (width, height), fit)

    # Divide out any frame the input already carries, then re-apply this one.
    with np.errstate(divide="ignore", invalid="ignore"):
        content = np.where(
            frame > 0.0,
            np.minimum(255.0, source[..., 3].astype(np.float64) * 255.0 / frame),
            0.0,
        )
    out_alpha = frame * content / 255.0
    return _save(
        _compose(source, out_alpha, frame >= MVP3_CONTENT_THRESHOLD, out_alpha),
        output_path,
    )


# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    import argparse

    versions = {"1": mvp1, "2": mvp2, "3": mvp3}
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("version", choices=sorted(versions), help="which MVP to apply")
    parser.add_argument("input", help="input image path")
    parser.add_argument("output", help="output PNG path")
    parser.add_argument("--fit", action="store_true",
                        help="scale-to-cover and centre-crop instead of stretching")
    args = parser.parse_args()
    written = versions[args.version](args.input, args.output, fit=args.fit)
    print(f"Saved {written} (mvp{args.version}, fit={args.fit})")
