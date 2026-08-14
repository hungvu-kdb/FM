"""Fit a compact rounded-rectangle plus detached-halo model to Root PNGs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from procedural_model import render_alpha, rounded_rect_sdf

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = HERE.parent / "Root"


def scalar(value: float, digits: int = 6) -> float:
    return round(float(value), digits)


def load_samples(root: Path) -> tuple[list[Path], np.ndarray]:
    paths = sorted(root.glob("*.png"))
    if not paths:
        raise FileNotFoundError(f"no PNG files found in {root}")
    alphas = []
    for path in paths:
        with Image.open(path) as image:
            if image.size != (260, 310):
                raise ValueError(f"{path.name}: expected 260x310, got {image.size}")
            alphas.append(np.asarray(image.convert("RGBA"), dtype=np.uint8)[..., 3])
    return paths, np.stack(alphas).astype(np.float64)


def sdf_for_geometry(width: int, height: int, values: dict[str, float]) -> np.ndarray:
    model = {**values, "width": width, "height": height}
    return rounded_rect_sdf(width, height, model)


def fit_one(alpha: np.ndarray) -> dict[str, float]:
    height, width = alpha.shape
    floor = float(np.median(alpha[alpha <= np.percentile(alpha, 15)]))
    peak = float(np.percentile(alpha, 99.5))
    threshold = floor + 0.5 * (peak - floor)
    mask = alpha >= threshold
    ys, xs = np.where(mask)
    if not len(xs):
        raise ValueError("sample has no detectable opaque content")

    left, right = float(xs.min()) - 0.5, float(xs.max()) + 0.5
    top, bottom = float(ys.min()) - 0.5, float(ys.max()) + 0.5
    geometry = {
        "center_x": (left + right) / 2.0,
        "center_y": (top + bottom) / 2.0,
        "half_width": (right - left) / 2.0,
        "half_height": (bottom - top) / 2.0,
    }

    # Radius is the scalar whose SDF sign best explains the observed threshold mask.
    best_radius, best_error = 0.0, np.inf
    corner_zone = ((np.abs(np.arange(width)[None, :] - geometry["center_x"]) > geometry["half_width"] - 20) &
                   (np.abs(np.arange(height)[:, None] - geometry["center_y"]) > geometry["half_height"] - 20))
    for radius in np.arange(2.0, 16.01, 0.25):
        candidate = {**geometry, "corner_radius": float(radius)}
        prediction = sdf_for_geometry(width, height, candidate) <= 0.0
        error = np.mean(prediction[corner_zone] != mask[corner_zone])
        if error < best_error:
            best_radius, best_error = float(radius), float(error)
    geometry["corner_radius"] = best_radius
    sdf = sdf_for_geometry(width, height, geometry)

    # Fit analytic edge width locally; broad interior/exterior pixels cannot dominate.
    edge_zone = np.abs(sdf) <= 2.5
    best_softness, best_edge_mse = 1.0, np.inf
    for softness in np.arange(0.25, 2.01, 0.05):
        coverage = np.clip(0.5 - sdf / softness, 0.0, 1.0)
        predicted = np.maximum(floor, peak * coverage)
        mse = np.mean((predicted[edge_zone] - alpha[edge_zone]) ** 2)
        if mse < best_edge_mse:
            best_softness, best_edge_mse = float(softness), float(mse)

    # Fit a *detached* one-sided Gaussian. Reduce pixels to robust radial-bin
    # medians, then grid-search gap/sigma and solve peak amplitude analytically.
    # Starting at d=3 excludes content-edge antialias from the halo fit.
    radial_distance: list[float] = []
    radial_alpha: list[float] = []
    quantized = np.rint(sdf * 4.0) / 4.0
    for distance in np.arange(3.0, 25.01, 0.25):
        values = alpha[quantized == distance]
        if values.size:
            radial_distance.append(float(distance))
            radial_alpha.append(float(np.median(values)))
    distances = np.asarray(radial_distance)
    observed = np.asarray(radial_alpha)
    best_halo_mse = np.inf
    halo_gap, halo_sigma, halo_peak = 9.0, 2.5, 100.0
    centered = observed - floor
    for candidate_gap in np.arange(6.0, 12.01, 0.25):
        for candidate_sigma in np.arange(0.75, 5.01, 0.05):
            basis = np.zeros_like(distances)
            active = distances >= candidate_gap
            basis[active] = np.exp(-0.5 * ((distances[active] - candidate_gap) / candidate_sigma) ** 2)
            denominator = float(np.dot(basis, basis))
            if denominator <= 0.0:
                continue
            amplitude = float(np.clip(np.dot(basis, centered) / denominator, 1.0, 254.0 - floor))
            predicted = floor + amplitude * basis
            mse = float(np.mean((predicted - observed) ** 2))
            if mse < best_halo_mse:
                best_halo_mse = mse
                halo_gap = float(candidate_gap)
                halo_sigma = float(candidate_sigma)
                halo_peak = floor + amplitude

    return {
        **{key: scalar(value) for key, value in geometry.items()},
        "edge_softness": scalar(best_softness),
        "content_alpha": scalar(peak),
        "alpha_floor": scalar(floor),
        "halo_gap": scalar(halo_gap),
        "halo_sigma": scalar(halo_sigma),
        "halo_peak": scalar(halo_peak),
        "corner_sign_error": scalar(best_error),
        "edge_rmse": scalar(np.sqrt(best_edge_mse)),
    }


def aggregate(fits: list[dict[str, float]], width: int, height: int) -> dict[str, float]:
    keys = (
        "center_x", "center_y", "half_width", "half_height", "corner_radius",
        "edge_softness", "content_alpha", "alpha_floor", "halo_gap",
        "halo_sigma", "halo_peak",
    )
    model: dict[str, float] = {"width": width, "height": height}
    for key in keys:
        model[key] = scalar(np.median([fit[key] for fit in fits]))
    return model


def distribution(values: np.ndarray) -> dict[str, float]:
    return {
        "min": scalar(np.min(values)),
        "p05": scalar(np.percentile(values, 5)),
        "p25": scalar(np.percentile(values, 25)),
        "median": scalar(np.median(values)),
        "p75": scalar(np.percentile(values, 75)),
        "p95": scalar(np.percentile(values, 95)),
        "max": scalar(np.max(values)),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fit and validate a scalar rounded-rectangle SDF plus detached Gaussian halo model."
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help=f"sample PNG directory (default: {DEFAULT_ROOT})")
    parser.add_argument("--model", type=Path, default=HERE / "model.json", help="output scalar model JSON")
    parser.add_argument("--diagnostic", type=Path, default=HERE / "generated_alpha.png", help="output generated alpha diagnostic PNG")
    parser.add_argument("--report", type=Path, default=HERE / "analysis_report.json", help="output fitting/validation report JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths, alphas = load_samples(args.root.resolve())
    height, width = alphas.shape[1:]
    fits = [fit_one(alpha) for alpha in alphas]
    model = aggregate(fits, width, height)
    generated = render_alpha(model)

    residuals = np.abs(alphas - generated[None, ...])
    sample_mae = residuals.mean(axis=(1, 2))
    sample_rmse = np.sqrt(np.mean(residuals ** 2, axis=(1, 2)))
    fit_parameter_summary = {
        key: distribution(np.asarray([fit[key] for fit in fits], dtype=np.float64))
        for key in model if key not in ("width", "height")
    }
    per_sample = [
        {
            "file": path.name,
            "alpha_mae": scalar(sample_mae[index]),
            "alpha_rmse": scalar(sample_rmse[index]),
            "fit": fits[index],
        }
        for index, path in enumerate(paths)
    ]
    report = {
        "sample_count": len(paths),
        "image_width": width,
        "image_height": height,
        "method": "per-sample scalar fitting followed by coordinate-wise median aggregation",
        "global_alpha_mae": scalar(np.mean(residuals)),
        "absolute_error_percentiles": {
            f"p{label}": scalar(np.percentile(residuals, percentile))
            for label, percentile in (("50", 50), ("75", 75), ("90", 90), ("95", 95), ("99", 99), ("99_9", 99.9))
        },
        "per_sample_alpha_mae_distribution": distribution(sample_mae),
        "per_sample_alpha_rmse_distribution": distribution(sample_rmse),
        "parameter_fit_distribution": fit_parameter_summary,
        "per_sample": per_sample,
    }

    for destination in (args.model, args.diagnostic, args.report):
        destination.resolve().parent.mkdir(parents=True, exist_ok=True)
    args.model.resolve().write_text(json.dumps(model, indent=2) + "\n", encoding="utf-8")
    Image.fromarray(np.rint(generated).astype(np.uint8), "L").save(args.diagnostic.resolve())
    args.report.resolve().write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    p = report["absolute_error_percentiles"]
    print(f"Analyzed {len(paths)} samples from {args.root.resolve()}")
    print(f"Saved scalar model: {args.model.resolve()}")
    print(f"Saved generated alpha: {args.diagnostic.resolve()}")
    print(f"Saved report: {args.report.resolve()}")
    print(f"Alpha MAE={report['global_alpha_mae']:.4f}; |error| p50={p['p50']:.2f}, p90={p['p90']:.2f}, p95={p['p95']:.2f}, p99={p['p99']:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
