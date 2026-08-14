# PROCESS.md — MVP3: how this was built, without Python

## Constraint

MVP3 must not use Python. It also must not repeat MVP1's dense alpha template
or MVP2's geometric signed-distance-field reconstruction.

## Runtime choice

Checked what the machine actually has: Node.js and .NET are installed; Go,
Rust, and ImageMagick are not. Node.js was chosen because its standard library
ships `zlib`, which is the only hard requirement for reading and writing PNG.

**Zero third-party packages.** No `npm install` at any point. The only imports
are `node:zlib`, `node:fs`, `node:path`, and `node:assert`.

## Step A — survey the input format

Before writing a decoder, I scanned the IHDR of all 46 files to learn exactly
which PNG variants must be supported:

```
29 files  260x310  depth=8  colour=3 (palette + tRNS)  + iTXt
15 files  260x310  depth=8  colour=6 (RGBA)
 2 files  260x310  depth=8  colour=3 (palette + tRNS)
```

All 8-bit and non-interlaced. So the decoder needs palette-with-transparency
and RGBA, and can reject interlacing and other bit depths loudly instead of
guessing.

## Step B — write the PNG codec (`png.mjs`)

- Verify the 8-byte signature, then walk the chunk stream reading `IHDR`,
  `PLTE`, `tRNS`, and concatenating `IDAT`.
- `inflateSync` the image data, then reverse the five PNG scanline filters
  (None, Sub, Up, Average, Paeth).
- Expand palette indices through `PLTE`/`tRNS` into straight RGBA, so
  everything downstream sees one uniform pixel layout.
- Writer emits filter-0 scanlines and `deflateSync` at level 9. Both RGBA and
  greyscale output are supported.
- Round-trip is asserted lossless in `verify.mjs`.

## Step C — measure cross-image agreement (`analyze.mjs`)

Computed per-pixel mean and standard deviation of alpha over all 46 samples:
mean std **0.4022**, max std **25.70**. The alpha field does not depend on the
portrait, so fitting one shared field is sound. The max of 25.7 is localised on
the content edge, where individual images antialias differently.

## Step D — fit the separable model

Instead of storing the field, factor it. Each rank-1 term is extracted by
alternating power iteration (120 sweeps), then deflated out of the residual so
the next term fits what remains. See `MATH.md` for the equations.

The singular values fall off a cliff — 63 393 then 1 147 — which confirms the
frame is nearly a pure product of a row profile and a column profile. Rank 8
stores 4 568 numbers, 5.7 % of a dense 260×310 matrix.

I compared rank 8 with rank 12. Rank 12 fits the mean field better (MAE 0.0529
vs 0.0667) but agreement with real samples does not improve (median per-sample
MAE 0.3481 vs 0.3470), meaning the extra terms are absorbing noise. Rank 8 ships.

## Step E — the apply program (`apply-frame.mjs`)

```
node MVP3/apply-frame.mjs INPUT [OUTPUT] [--model FILE] [--fit] [--no-resize]
```

- Rebuilds the frame from the profiles at run time — the model file holds no
  rendered image.
- Off-size input is bilinearly resampled to 260×310. `--fit` instead scales to
  cover and centre-crops, so the subject is not lost to the rounded corners.
  `--no-resize` rejects off-size input rather than rescaling it.
- Composites per `MATH.md` §6.

### One correction made during validation

The first version multiplied source alpha by frame alpha directly. The
idempotency check caught it: re-applying the frame darkened the glow by up to
64 levels, because the glow gradient was being multiplied twice. Fixed by
normalising the source alpha against the frame before re-applying it. Max
channel delta on re-apply is now **0**.

## Step F — validation (`verify.mjs`)

```
node MVP3/verify.mjs      →  8/8 checks passed
```

1. Model holds separable terms only, no 2-D matrix — 4 568 vs 80 600 numbers.
2. RGBA PNG round-trip is byte-exact.
3. Greyscale PNG round-trip is byte-exact.
4. Rendered frame matches real samples — MAE 0.285–0.347, ≥97.1 % within ±3.
5. Apply output on the 253×336 test portrait is a clean 260×310 RGBA PNG.
6. Outer glow is pure black; centre pixel alpha is 255.
7. Transformation is idempotent — max channel delta 0.
8. A fully transparent input produces a fully transparent output.

Results are also written to `verification.json`.

## Files

| File | Role |
|---|---|
| `png.mjs` | PNG decode/encode on `node:zlib` alone |
| `separable.mjs` | rank-1 extraction, deflation, frame rendering |
| `analyze.mjs` | Step 1 — fit the model from `Root/` |
| `apply-frame.mjs` | Step 2 — apply the frame to your portrait |
| `verify.mjs` | assertion suite, writes `verification.json` |
| `model.json` | rank-8 profiles and weights |
| `analysis_report.json` | spectrum and per-sample error metrics |
| `generated_alpha.png` | greyscale preview of the rendered frame |

## Commands

```powershell
node MVP3\analyze.mjs --rank 8
node MVP3\apply-frame.mjs Test\alavez.png TestOutputs\MVP3\alavez.png
node MVP3\verify.mjs
```
