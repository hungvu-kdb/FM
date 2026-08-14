# PROCESS.md — How the pattern was found and how to use the tools

## Overview

The goal (from `description.md`) has two steps:

1. **Formalize** the common pattern of the FM player portraits in `Root/`.
2. **Build an apply program** that takes a 260×310 picture and reproduces the
   same special border (transparent edge + gradient glow), so a custom youngster
   portrait can be dropped into Football Manager.

The mathematical model is in `MATH.md`. This file documents the investigation
process and the practical usage.

## Investigation steps

1. **Inventory** (`analyze.py`)
   - 46 PNGs, all exactly **260×310**, modes `P` (palette) and `RGBA`.
   - Converted every image to RGBA and stacked the alpha channels.

2. **Discovered the alpha is a fixed template**
   - Per-pixel std of alpha across the 46 images is ≈ 0
     (98.5 % of pixels have std < 5).
   - Conclusion: the "border + gradient" is **image-independent** — a constant
     alpha matrix applied to every portrait.

3. **Characterized the border geometry** (`analyze2.py`, `analyze3.py`)
   - Along any scan line the alpha shows three zones:
     - **Outer glow**: smooth ramp 0 → ~100 over ~9 px.
     - **Transparent gap**: alpha ≈ 0.
     - **Content region**: hard edge, alpha = 255 (rounded rectangle,
       bbox x[19..241], y[18..292]).

4. **Identified the glow colour** (`analyze4.py`)
   - In every sample the glow pixels are **pure black** `(0,0,0)` with only the
     alpha varying. So the glow is a black soft-shadow, independent of portrait
     content.

5. **Built the canonical template** (`build_template.py`)
   - `T = round(mean alpha)`, denoised (values < 1.5 → 0), plateau snapped to 255.
   - Saved as `template_alpha.npy` (the machine-usable matrix),
     `template_alpha.png` (grayscale view) and `template_preview.png`.

6. **Wrote and tested the apply program** (`apply_border.py`, `test_apply.py`)
   - Verified output alpha equals the template, glow region is black, content
     is preserved, and the result matches real samples (97–99 % of alpha pixels
     within ±3).

## Files produced

| File                    | Purpose                                             |
|-------------------------|-----------------------------------------------------|
| `analyze.py`            | Step-1 inventory + alpha stack statistics           |
| `analyze2.py`/`3`/`4.py`| Step-1 geometry & colour characterization           |
| `build_template.py`     | Builds `template_alpha.npy` (the model)             |
| `template_alpha.npy`    | **The canonical alpha template matrix T** (260×310) |
| `template_alpha.png`    | Grayscale visualization of T                        |
| `template_preview.png`  | RGBA preview (black glow + white content)           |
| `apply_border.py`       | **Step-2 apply program**                            |
| `test_apply.py`         | Self-test / validation                              |
| `MATH.md`               | Formal mathematical model                           |
| `PROCESS.md`            | This document                                       |
| `Memory.md`             | Checkpoint / progress log                           |

## How to use the apply program

Requirements: Python 3 with `numpy` and `Pillow`.

Pixel-aligned (input already framed the way FM portraits are, fills full 260×310):

```
python apply_border.py my_portrait.png
# -> my_portrait_fm.png
```

Specify an output name:

```
python apply_border.py my_portrait.png youngster_1234.png
```

Fit mode (scale + center-crop your photo to cover the content area so nothing
important is lost to the rounded corners):

```
python apply_border.py my_portrait.png youngster_1234.png --fit
```

Notes:
- Any input size is accepted; it is resized to 260×310 (default) or scaled to
  cover the content box (`--fit`).
- The output is always a 260×310 RGBA PNG with the exact FM frame, ready to be
  used as a Football Manager portrait.
- To place it in the game, name the file with the player's UID and reference it
  in the graphics `config.xml` (standard FM skinning workflow).
