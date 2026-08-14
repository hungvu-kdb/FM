# MVP2 checkpoint

## Current checkpoint

- Read `../description.md` and inspected all 46 sibling `Root/*.png` files.
- Confirmed every sample is 260x310; sources include palette and RGBA PNGs.
- Chosen model: rounded-rectangle signed distance, analytical edge coverage, and detached exterior-only Gaussian black halo.
- Constraint honored: no MVP1 alpha matrix/template or `template == 255` content classification is copied or reused.

## Commands

```powershell
python d:\Random\Pic\MVP2\analyze.py
python d:\Random\Pic\MVP2\apply_frame.py d:\Random\Pic\MVP1\test_input.png d:\Random\Pic\MVP2\test_output.png
python -m py_compile d:\Random\Pic\MVP2\procedural_model.py d:\Random\Pic\MVP2\analyze.py d:\Random\Pic\MVP2\apply_frame.py
```

## Outputs and validation status

Completed outputs:

- `model.json`: 13 scalar numeric values only; no list/dict/matrix payload.
- `generated_alpha.png`: 260x310 `L`, analytically rendered diagnostic.
- `analysis_report.json`: 46 per-sample scalar fits and aggregate metrics.
- `test_output.png`: generated from suitable 260x310 RGB `../MVP1/test_input.png`; output is 260x310 RGBA.

Validation **passed**:

- `python -m py_compile procedural_model.py analyze.py apply_frame.py`
- IDE diagnostics: no issues in all three Python files.
- Global alpha MAE across all Root samples: `1.433060`.
- Absolute-error p50/p90/p95/p99: `0.0 / 2.798910 / 6.762470 / 25.887878`.
- Per-sample MAE min/median/p95/max: `1.350232 / 1.436951 / 1.479124 / 1.810454`.
- Model medians: center `(130,154.5)`, half-size `(111.5,138)`, radius `5.25`, edge softness `1`, gap `9`, sigma `3`, halo peak `72.092695`, floor `1`, content alpha `255`.
- Assertions passed for source-alpha accounting, RGB retention in content, and black halo RGB.
- Both `--help` commands passed; paths work independently of current working directory.
- No `.npy`, per-pixel alpha template, or formal test suite added.

## 2026-08-13 — Comparison notebook integration ✅
- Executed notebook: `../compare_mvp_outputs.ipynb` (fallback exact-cell execution because `nbformat`, `nbclient`, and IPython are unavailable in `C:\Python314\python.exe`; outputs are saved in the notebook).
- Top-level test input: `../Test/alavez.png` (253×336 RGBA).
- Actual CLI invoked with explicit output and required `--resize`: `apply_frame.py`; this directly resizes non-260×310 input to 260×310.
- Outputs: `../TestOutputs/MVP2/alavez.png`; comparison: `../TestOutputs/Comparisons/alavez.png_comparison.png`.
- Validation passed: subprocess return 0, output exists, 260×310, RGBA.
