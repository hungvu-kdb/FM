# Memory.md — Checkpoint

## Task
From `description.md`: analyze FM player portraits in `Root/`, formalize the
common border/gradient pattern (Step 1), and build an apply program for custom
260×310 portraits (Step 2). Document math in `MATH.md` and process in
`PROCESS.md`.

## Status: COMPLETE ✅

### Step 1 — Formalization (DONE)
- 46 samples, all 260×310. Alpha channel is a **fixed template** across all
  images (per-pixel std ≈ 0; 98.5% of pixels std < 5).
- Border = 3 zones: black outer glow (alpha ramp 0→~100), transparent gap,
  opaque rounded-rectangle content region (bbox x[19..241], y[18..292], 75.7%).
- Glow colour is pure black (0,0,0) in every sample.
- Model written in `MATH.md`: `O = [ P ⊙ Ω ‖ T ]`.
- Canonical template saved: `template_alpha.npy` (+ png previews).

### Step 2 — Apply program (DONE)
- `apply_border.py`: composites a 260×310 portrait into the frame.
  - default mode: pixel-aligned full-frame.
  - `--fit` mode: scale-to-cover content box + center-crop.
- Output = 260×310 RGBA PNG with exact template alpha.

### Validation (DONE)
- `test_apply.py` all asserts pass.
- Output alpha vs real sample 1000050: mean |Δ|=0.31, 97.8% within ±3.
- Re-applied on 100013: mean |Δ|=0.22, 98.7% within ±3.

## Artifacts
analyze.py, analyze2.py, analyze3.py, analyze4.py, build_template.py,
apply_border.py, test_apply.py, template_alpha.npy/.png, template_preview.png,
MATH.md, PROCESS.md.
Test outputs: test_input.png, test_output.png, test_output_fit.png,
mean_alpha.png/.npy, std_alpha.png.

## Next (optional, not requested)
- Skin/config.xml generation to wire portraits into FM by UID.
- Batch mode to process a folder of portraits at once.

## 2026-08-13 — Comparison notebook integration ✅
- Executed notebook: `../compare_mvp_outputs.ipynb` (fallback exact-cell execution because `nbformat`, `nbclient`, and IPython are unavailable in `C:\Python314\python.exe`; outputs are saved in the notebook).
- Top-level test input: `../Test/alavez.png` (253×336 RGBA).
- Actual CLI invoked with explicit output: `apply_border.py`; its default policy directly resizes non-260×310 input to 260×310.
- Outputs: `../TestOutputs/MVP1/alavez.png`; comparison: `../TestOutputs/Comparisons/alavez.png_comparison.png`.
- Validation passed: subprocess return 0, output exists, 260×310, RGBA.
