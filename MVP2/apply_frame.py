"""Apply the scalar procedural Football Manager portrait frame."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from procedural_model import MODEL_KEYS, render_alpha, rounded_rect_sdf

HERE = Path(__file__).resolve().parent
DEFAULT_MODEL = HERE / "model.json"


def load_model(path: Path) -> dict[str, float]:
    data = json.loads(path.read_text(encoding="utf-8"))
    missing = [key for key in MODEL_KEYS if key not in data]
    if missing:
        raise ValueError(f"model is missing scalar parameters: {', '.join(missing)}")
    for key in MODEL_KEYS:
        if isinstance(data[key], (dict, list)) or not isinstance(data[key], (int, float)):
            raise ValueError(f"model parameter {key!r} must be scalar")
    return data


def apply_frame(source: Image.Image, model: dict[str, float], resize: bool = False) -> Image.Image:
    target = (int(model["width"]), int(model["height"]))
    rgba = source.convert("RGBA")
    if rgba.size != target:
        if not resize:
            raise ValueError(f"input must be {target[0]}x{target[1]}; got {rgba.size[0]}x{rgba.size[1]}")
        rgba = rgba.resize(target, Image.Resampling.LANCZOS)

    src = np.asarray(rgba, dtype=np.uint8)
    out_alpha = render_alpha(model, src[..., 3])
    sdf = rounded_rect_sdf(target[0], target[1], model)
    content_coverage = np.clip(0.5 - sdf / max(float(model["edge_softness"]), 1e-6), 0.0, 1.0)

    # Straight-alpha RGBA: retain source RGB wherever procedural content contributes;
    # black is intentional in the halo and fully transparent exterior.
    out_rgb = np.zeros_like(src[..., :3])
    content_pixels = content_coverage > 0.0
    out_rgb[content_pixels] = src[..., :3][content_pixels]
    out = np.dstack((out_rgb, np.rint(out_alpha).astype(np.uint8)))
    return Image.fromarray(out, "RGBA")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply a rounded-rectangle portrait mask and detached black Gaussian halo."
    )
    parser.add_argument("input", type=Path, help="input portrait (normally 260x310; RGB or RGBA)")
    parser.add_argument("output", nargs="?", type=Path, help="output RGBA PNG (default: INPUT_mvp2.png)")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL, help=f"scalar model JSON (default: {DEFAULT_MODEL})")
    parser.add_argument("--resize", action="store_true", help="resize a non-260x310 input instead of rejecting it")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output or args.input.with_name(args.input.stem + "_mvp2.png")
    model = load_model(args.model.resolve())
    with Image.open(args.input) as source:
        result = apply_frame(source, model, resize=args.resize)
    output.parent.mkdir(parents=True, exist_ok=True)
    result.save(output, format="PNG")
    print(f"Saved {output.resolve()} ({result.width}x{result.height}, {result.mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
