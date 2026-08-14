"""Apply the Football Manager portrait border to a 260x310 input image.

Usage:
    python apply_border.py INPUT [OUTPUT] [--fit]

The transformation composites your portrait into the canonical FM portrait
frame defined by template_alpha.npy:

    out.RGB[p] = portrait.RGB[p]   if p in content region (opaque)
               = (0,0,0)           elsewhere (black outer glow)
    out.A[p]   = template_alpha[p]

Modes:
    default : pixel-aligned. Your 260x310 image is masked directly by the
              template (edges outside the rounded content area are clipped).
    --fit   : your portrait is scaled to cover the content bounding box,
              so nothing important is lost to the rounded corners.
"""
import os
import sys
import numpy as np
from PIL import Image

BASE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(BASE, "template_alpha.npy")

TARGET_SIZE = (260, 310)  # (W, H)


def load_template():
    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError(
            "template_alpha.npy not found. Run build_template.py first."
        )
    return np.load(TEMPLATE_PATH)  # (H, W) uint8


def content_bbox(content_mask):
    ys, xs = np.where(content_mask)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1  # x0,y0,x1,y1


def apply_border(portrait: Image.Image, template: np.ndarray, fit: bool = False) -> Image.Image:
    H, W = template.shape
    content_mask = template == 255

    if fit:
        # Scale portrait to cover content bbox, then place it.
        x0, y0, x1, y1 = content_bbox(content_mask)
        bw, bh = x1 - x0, y1 - y0
        src = portrait.convert("RGB")
        sw, sh = src.size
        scale = max(bw / sw, bh / sh)
        new = (max(1, round(sw * scale)), max(1, round(sh * scale)))
        src = src.resize(new, Image.LANCZOS)
        # center-crop to bbox size
        left = (src.size[0] - bw) // 2
        top = (src.size[1] - bh) // 2
        src = src.crop((left, top, left + bw, top + bh))
        canvas = np.zeros((H, W, 3), dtype=np.uint8)
        canvas[y0:y1, x0:x1] = np.asarray(src)
        rgb = canvas
    else:
        # Pixel-aligned: portrait must fill the full 260x310 frame.
        src = portrait.convert("RGB")
        if src.size != TARGET_SIZE:
            src = src.resize(TARGET_SIZE, Image.LANCZOS)
        rgb = np.asarray(src).copy()

    # Force black everywhere outside the content region (the glow is black).
    rgb[~content_mask] = 0

    out = np.dstack([rgb, template]).astype(np.uint8)
    return Image.fromarray(out, mode="RGBA")


def main():
    args = [a for a in sys.argv[1:]]
    fit = "--fit" in args
    args = [a for a in args if a != "--fit"]
    if not args:
        print(__doc__)
        sys.exit(1)
    inp = args[0]
    out = args[1] if len(args) > 1 else os.path.splitext(inp)[0] + "_fm.png"

    template = load_template()
    portrait = Image.open(inp)
    result = apply_border(portrait, template, fit=fit)
    result.save(out)
    print(f"Saved {out}  ({result.size[0]}x{result.size[1]}, mode={result.mode}, fit={fit})")


if __name__ == "__main__":
    main()
