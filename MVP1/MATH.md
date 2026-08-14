# MATH.md — Mathematical Representation of the FM Portrait Frame

## 1. Objects and notation

Each portrait is an RGBA image of fixed size

```
W = 260   (width)
H = 310   (height)
```

Represent one image as a tensor

```
I ∈ {0,…,255}^{H × W × 4},   channels (R, G, B, A)
```

We split it into a colour part and an alpha (opacity) part:

```
C = I[:, :, 0:3]   ∈ {0,…,255}^{H×W×3}     (colour)
A = I[:, :, 3]     ∈ {0,…,255}^{H×W}       (alpha / transparency)
```

The dataset is the set of N = 46 sample images `{ I⁽ᵏ⁾ }`, k = 1…N, all
sharing the same size and, as shown below, the **same alpha matrix**.

## 2. Key empirical finding — the alpha channel is a constant template

Stack all sample alphas into `𝒜 ∈ ℝ^{N×H×W}` and compute the per-pixel mean
and standard deviation:

```
M(y,x) = (1/N) Σ_k 𝒜_k(y,x)          (mean alpha)
S(y,x) = sqrt( (1/N) Σ_k (𝒜_k(y,x) − M(y,x))² )   (std)
```

Measured result:

```
mean of S over all pixels = 0.40
max  of S                 = 25.7
P[ S < 5 ] = 98.5 %        P[ S < 1 ] = 87.7 %
```

Because the standard deviation is ≈ 0 almost everywhere, the alpha channel is
**not** image-dependent. It is a fixed **template matrix**

```
T ≈ M   (snapped to clean values),   T ∈ {0,…,255}^{H×W}
```

This `T` is exactly the "transparent border with a gradient" the user feels.

## 3. Structure of the template T

Scanning any line through `T` reveals three concentric zones (values are alpha):

```
outer glow           gap        content region        gap     outer glow
0 1 2 5 17 25 40 56 76 98 | 0 0 0 0 0 0 0 0 | 255 255 … 255 | 0 0 … 0 | 98 76 … 1
   x = 0 … 9              x = 10 … 18          x = 19 … 241
```

### Zone 1 — Outer glow (soft halo)
A smooth alpha ramp from 0 up to ≈ 98–100 over ~9 px on every side, following
the rounded outline. Its **colour is pure black** `(0,0,0)` in every sample
(measured glow-mean RGB ≈ (0.4, 0.4, 0.4)). It is a drop-shadow / glow, not
part of the portrait.

### Zone 2 — Transparent gap
A band of alpha ≈ 0 separating the glow from the content. This gap is what
makes the glow read as a detached soft shadow.

### Zone 3 — Content region Ω (opaque)
A hard-edged **rounded rectangle** where `T = 255`. This is where the portrait
is shown.

```
Content bounding box:   x ∈ [19, 241],  y ∈ [18, 292]
Content area:           60 998 px  (75.7 % of the frame)
Glow area:               9 601 px  (11.9 % of the frame)
```

Define the binary content mask

```
Ω(y,x) = 1  ⇔  T(y,x) = 255
```

## 4. The transformation (compositing operator)

Given an input portrait `P ∈ {0,…,255}^{H×W×3}` (colour only), the frame is
applied by a per-pixel operator `Φ` that produces the output `O`:

```
O_RGB(y,x) = P(y,x) · Ω(y,x)          (portrait inside Ω, black = 0 outside)
O_A(y,x)   = T(y,x)                    (alpha copied from the template)
```

In compact matrix form (⊙ = element-wise / Hadamard product, broadcast over the
3 colour channels):

```
O = [ P ⊙ Ω  ‖  T ]
```

where `‖` denotes channel concatenation of the 3-channel colour with the
1-channel alpha.

Properties:
- `Φ` is **idempotent**: applying the frame to an already-framed image gives the
  same result, because `Ω⊙Ω = Ω` and the alpha is overwritten by `T`.
- The colour outside `Ω` is forced to black so the glow (which is black at
  fractional alpha) is reproduced exactly.

### Optional "fit" variant
To avoid losing content to the rounded corners, the portrait may first be
scaled to **cover** the content bounding box `B = [19,241]×[18,292]`
(size 222×274) and center-cropped, then composited by the same `Φ`:

```
P' = CenterCrop_B( Resize_cover( P, B ) )
O  = [ P' ⊙ Ω  ‖  T ]
```

## 5. Validation

Reconstructing `T` and comparing to real samples' alpha channels:

```
vs sample 1000050:  mean |ΔA| = 0.31,  97.8 % of pixels within ±3
re-applied 100013:  mean |ΔA| = 0.22,  98.7 % of pixels within ±3
```

The small residuals come from per-image antialiasing of the content edge; the
template is otherwise an exact model of the frame.
