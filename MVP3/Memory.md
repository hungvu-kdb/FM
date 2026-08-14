# MVP3 checkpoint

## 2026-08-13 — MVP3 complete (no Python) ✅

### Constraint
- No Python anywhere. No third-party packages either.
- Must not reuse MVP1's dense alpha template or MVP2's signed-distance-field geometry.

### Runtime
- Probed the machine: Node.js and .NET present; Go, Rust, `pwsh`, ImageMagick absent.
- Chose **Node.js ESM** (`.mjs`). Only imports are `node:zlib`, `node:fs`, `node:path`, `node:assert`.
- Wrote a PNG codec by hand because there is no Pillow equivalent available without npm.

### Input format survey
- 29 files: palette + tRNS + iTXt; 15 files: RGBA; 2 files: palette + tRNS.
- All 260×310, 8-bit, non-interlaced.

### Model — separable low-rank factorization
- `A(y,x) ≈ clamp(Σ_k s_k · u_k(y) · v_k(x), 0, 255)`, profiles unit-norm.
- Fitted by alternating power iteration (120 sweeps) + deflation. No linear-algebra lib.
- Cross-image alpha std: mean `0.4022`, max `25.70` → shared field justified.
- Spectrum: `63393.9, 1147.4, 674.4, 495.0, 344.1, 192.6, 131.5, 120.4` — nearly rank 1.
- Shipped **rank 8**: 4 568 numbers vs 80 600 dense (5.7 %).
- Rank 12 fits the mean field better (0.0529 vs 0.0667) but per-sample MAE does not improve
  (0.3481 vs 0.3470), so rank 8 avoids fitting antialiasing noise.

### Accuracy
- vs mean field: MAE `0.0667`, p50 `0.0017`, p90 `0.0699`, p99 `1.8707`, max `13.80`.
- Per-sample MAE: min `0.2444` / median `0.3470` / mean `0.3395` / max `0.9342`.
- Spot samples: `1000050.png` 0.347 (97.1 % ±3), `100013.png` 0.285 (98.6 % ±3).

### Correction during validation
- v1 multiplied source alpha by frame alpha, which broke idempotency (max delta 64 on
  re-apply, glow darkened twice). Fixed by normalising source alpha against the frame
  before re-applying. Max channel delta on re-apply is now **0**.

### Validation — 8/8 passed (`node MVP3\verify.mjs`)
- Separable-only model; RGBA and greyscale PNG round-trips byte-exact; frame matches real
  samples; 253×336 → 260×310 RGBA output; glow pure black + centre alpha 255; idempotent;
  transparent input stays transparent.
- Results also written to `verification.json`.

### Artifacts
`png.mjs`, `separable.mjs`, `analyze.mjs`, `apply-frame.mjs`, `verify.mjs`,
`model.json`, `analysis_report.json`, `verification.json`, `generated_alpha.png`,
`MATH.md`, `PROCESS.md`.
Test output: `../TestOutputs/MVP3/alavez.png`.

### Commands
```powershell
node MVP3\analyze.mjs --rank 8
node MVP3\apply-frame.mjs Test\alavez.png TestOutputs\MVP3\alavez.png
node MVP3\verify.mjs
```

### Also produced
- `../analysis_report.html` — tabbed HTML report covering all three MVPs.
