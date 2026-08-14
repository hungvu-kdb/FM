# MVP2 process

This document is completed from the measurements emitted by `analyze.py`. MVP2 inspects every PNG in sibling `Root/`, fits scalar geometry and halo parameters per image, robustly aggregates them with medians, renders a fresh analytical alpha field, and validates that field against every source alpha channel.

Run from any working directory:

```powershell
python d:\Random\Pic\MVP2\analyze.py
python d:\Random\Pic\MVP2\apply_frame.py d:\Random\Pic\MVP1\test_input.png d:\Random\Pic\MVP2\test_output.png
```

The scripts resolve default data/model/output locations relative to their own files. `analyze.py --help` and `apply_frame.py --help` describe overrides. NumPy and Pillow are the only non-stdlib dependencies.

## Method

1. Convert all samples to RGBA and inspect alpha.
2. For each sample, threshold halfway between its transparent floor and opaque plateau; infer content bounds and select the corner radius whose rounded-rectangle SDF sign best matches corner pixels.
3. Fit antialias width only near the SDF zero crossing.
4. Locate the detached halo's nearest exterior distance and infer Gaussian sigma from the log-linearized outward decay.
5. Median-aggregate each fitted physical scalar. No image matrix is aggregated or serialized.
6. Render `generated_alpha.png` from formulas and report per-sample/global residual statistics in `analysis_report.json`.

## Measured result and validation

All 46 samples were used. Median-aggregated parameters are center `(130.0, 154.5)`, half-size `(111.5, 138.0)`, radius `5.25 px`, edge softness `1.0 px`, content alpha `255`, floor alpha `1`, detached gap `9.0 px`, halo sigma `3.0 px`, and fitted halo amplitude/peak `72.092695`.

Across all `46 x 260 x 310` alpha values, MAE is **1.433060**. Absolute-error percentiles are p50 `0.000`, p75 `0.000`, p90 `2.798910`, p95 `6.762470`, p99 `25.887878`, and p99.9 `99.000`. Per-image MAE has min `1.350232`, median `1.436951`, p95 `1.479124`, and max `1.810454` (the worst sample is `1000924.png`). The larger tail is localized mainly to analytical corner/edge approximation and the halo's abrupt detached onset.

Validation completed: all Python files compile; IDE diagnostics are clean; both CLIs expose useful help; `generated_alpha.png` is 260x310 `L`; `test_output.png` is 260x310 `RGBA`; the JSON contains only scalar values; no NPY/template was produced; and targeted assertions confirm source alpha multiplication, source RGB preservation in content, and black RGB in halo pixels.

## Outputs

- `model.json`: scalar model parameters only
- `generated_alpha.png`: formula-generated diagnostic (not loaded by application)
- `analysis_report.json`: all-sample fits and error statistics
- `test_output.png`: smoke output made from `../MVP1/test_input.png`

## Difference from MVP1

MVP1 stores and reapplies a fixed 260x310 mean-alpha/template matrix and defines content using `template == 255`. MVP2 does neither. Its `model.json` contains only scalar dimensions, SDF geometry, edge coverage, and halo parameters. Every output alpha pixel is generated analytically; procedural SDF coverage, not equality to 255, determines where portrait RGB is retained. This is a fundamentally different inverse-graphics representation and is intentionally approximate rather than pixel-copying the training frame.
