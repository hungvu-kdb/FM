"""Compact procedural alpha renderer shared by analysis and application."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

import numpy as np

MODEL_KEYS = (
    "width", "height", "center_x", "center_y", "half_width", "half_height",
    "corner_radius", "edge_softness", "content_alpha", "alpha_floor",
    "halo_gap", "halo_sigma", "halo_peak",
)


def rounded_rect_sdf(width: int, height: int, model: Mapping[str, float]) -> np.ndarray:
    """Signed distance at pixel centres; negative values are inside."""
    y, x = np.mgrid[0:height, 0:width].astype(np.float64)
    qx = np.abs(x - float(model["center_x"])) - (
        float(model["half_width"]) - float(model["corner_radius"])
    )
    qy = np.abs(y - float(model["center_y"])) - (
        float(model["half_height"]) - float(model["corner_radius"])
    )
    outside = np.hypot(np.maximum(qx, 0.0), np.maximum(qy, 0.0))
    inside = np.minimum(np.maximum(qx, qy), 0.0)
    return outside + inside - float(model["corner_radius"])


def render_alpha(model: Mapping[str, float], source_alpha: np.ndarray | None = None) -> np.ndarray:
    """Render content coverage and a detached, exterior-only Gaussian halo."""
    width, height = int(model["width"]), int(model["height"])
    sdf = rounded_rect_sdf(width, height, model)
    softness = max(float(model["edge_softness"]), 1e-6)
    coverage = np.clip(0.5 - sdf / softness, 0.0, 1.0)
    content = float(model["content_alpha"]) * coverage
    if source_alpha is not None:
        if source_alpha.shape != (height, width):
            raise ValueError(f"source alpha must have shape {(height, width)}")
        content *= source_alpha.astype(np.float64) / 255.0

    floor = float(model["alpha_floor"])
    halo = np.full((height, width), floor, dtype=np.float64)
    gap = float(model["halo_gap"])
    active = sdf >= gap
    z = (sdf[active] - gap) / max(float(model["halo_sigma"]), 1e-6)
    halo[active] = floor + (float(model["halo_peak"]) - floor) * np.exp(-0.5 * z * z)
    return np.clip(np.maximum(content, halo), 0.0, 255.0)
