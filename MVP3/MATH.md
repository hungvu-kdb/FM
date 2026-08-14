# MATH.md — MVP3: Separable Low-Rank Factorization of the Alpha Field

## 1. Setup

Every sample in `Root/` is an RGBA raster of fixed size

```
W = 260,  H = 310,  N = 46 samples
```

Sample `k` splits into colour and alpha:

```
C⁽ᵏ⁾ = I⁽ᵏ⁾[:, :, 0:3] ∈ {0..255}^{H×W×3}
A⁽ᵏ⁾ = I⁽ᵏ⁾[:, :, 3]   ∈ {0..255}^{H×W}
```

## 2. Step 0 — is a shared alpha field justified?

Per-pixel mean and standard deviation across the 46 samples:

```
M(y,x) = (1/N) Σ_k A⁽ᵏ⁾(y,x)
S(y,x) = sqrt( (1/N) Σ_k (A⁽ᵏ⁾(y,x) − M(y,x))² )
```

Measured on the full set:

```
mean_{y,x} S = 0.4022
max_{y,x}  S = 25.70
```

The alpha field is effectively image-independent, so a single shared field `M`
is a valid modelling target. MVP3 then asks a different question from the
earlier attempts: **not what shape is this, but what is its algebraic rank?**

## 3. The model — a rank-K separable sum

Treat `M` as a real matrix `M ∈ ℝ^{H×W}` and approximate it by a sum of
*outer products* of one-dimensional profiles:

```
Â = Σ_{k=1..K} s_k · u_k ⊗ v_k          u_k ∈ ℝ^H,  v_k ∈ ℝ^W,  s_k ∈ ℝ

Â(y,x) = clamp( Σ_{k=1..K} s_k · u_k(y) · v_k(x) , 0, 255 )
```

with the profiles normalised to unit length, `‖u_k‖₂ = ‖v_k‖₂ = 1`.

This is the truncated singular value decomposition of `M`, written in
separable form. The stored model is only the profiles and weights:

```
parameter count = K · (H + W + 1) = 8 · (310 + 260 + 1) = 4 568 numbers
dense matrix    = H · W                                 = 80 600 numbers
compression     = 5.7 % of the parameters
```

The important structural claim: **the frame is a product of a vertical profile
and a horizontal profile**, not a 2-D picture and not a geometric shape.

## 4. Fitting — alternating power iteration with deflation

No linear-algebra library is used. Each rank-1 term is found by the fixed-point
iteration that an SVD converges to. Starting from `v ← 1/√W · 1`:

```
repeat T = 120 times:
    u ← R v         ;  u ← u / ‖u‖₂
    v ← Rᵀ u        ;  v ← v / ‖v‖₂
s  ← uᵀ R v
```

`u` and `v` converge to the leading singular vectors of the current residual
`R`, and `s` to the leading singular value. The term is then removed
(*deflation*) and the next term is fitted to what is left:

```
R⁽⁰⁾ = M
R⁽ᵏ⁾ = R⁽ᵏ⁻¹⁾ − s_k · u_k ⊗ v_k
```

## 5. Measured spectrum

The singular values collapse immediately, which is the empirical evidence that
the frame really is near-separable:

| K | weight `s_K` | MAE of `Â` vs `M` |
|---|---|---|
| 1 | 63 393.9 | 0.6237 |
| 2 | 1 147.4 | 0.3549 |
| 3 | 674.4 | 0.2789 |
| 4 | 495.0 | 0.1607 |
| 5 | 344.1 | 0.1224 |
| 6 | 192.6 | 0.0982 |
| 7 | 131.5 | 0.0803 |
| 8 | 120.4 | 0.0667 |

`s_1` carries ~98 % of the spectral energy: the frame is *almost* exactly
rank 1, i.e. very nearly `alpha(y,x) = f(y)·g(x)`. Terms 2–8 correct the
rounded corners and the glow falloff, where the row and column profiles are
not perfectly independent.

`K = 8` is the shipped default. Beyond it the added terms begin fitting
per-image antialiasing noise: rank 12 lowers the error against the mean field
(0.0529) but does not improve agreement with actual samples.

## 6. The compositing operator

Let `Â` be the rendered frame. Given input `P` with alpha `A_P`, first
*normalise away* any frame the input already carries, then re-apply:

```
A_content(y,x) = clamp( 255 · A_P(y,x) / Â(y,x) , 0, 255 )         (Â > 0)
A_out(y,x)     = Â(y,x) · A_content(y,x) / 255

RGB_out(y,x)   = RGB_P(y,x)   if Â(y,x) ≥ 128       (content)
               = (0,0,0)      otherwise             (black glow)
```

Properties:

- **Idempotent, exactly.** Re-applying the frame changes no channel by even 1
  (measured max delta = 0). The division by `Â` cancels the multiplication.
- **Transparency-preserving.** A fully transparent input stays fully
  transparent; a soft cut-out keeps its own gradient.
- **Glow colour.** Black outside the content threshold reproduces the measured
  glow, which is pure `(0,0,0)` in every sample.

## 7. Validation

Rendered rank-8 frame against real sample alphas:

```
1000050.png   MAE = 0.347   97.1 % of pixels within ±3
100013.png    MAE = 0.285   98.6 % within ±3
1002273.png   MAE = 0.347   97.1 % within ±3

across all 46 samples:  MAE min 0.2444 / median 0.3470 / mean 0.3395 / max 0.9342
against the mean field: MAE 0.0667,  p50 0.0017,  p90 0.0699,  p99 1.8707
```

The residual is per-image antialiasing on the content edge, the same
irreducible term the other two models hit.
