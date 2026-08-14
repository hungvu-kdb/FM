"""Build the canonical border template (alpha matrix + content mask) from samples.

The template is derived by averaging the alpha channels of all Root samples,
then snapping to clean values. It captures:
  - the black outer glow (gradient alpha)
  - the transparent gap
  - the opaque rounded-rectangle content region
"""
import os, glob
import numpy as np
from PIL import Image

BASE = os.path.dirname(__file__)
ROOT = os.path.join(BASE, "Root")
files = sorted(glob.glob(os.path.join(ROOT, "*.png")))

alphas = []
for f in files:
    im = Image.open(f).convert("RGBA")
    alphas.append(np.asarray(im)[:, :, 3].astype(np.float64))

A = np.stack(alphas, axis=0)          # (N, H, W)
mean_alpha = A.mean(axis=0)           # (H, W)
H, W = mean_alpha.shape

# --- Snap to clean template ---
template = mean_alpha.copy()
template[template < 1.5] = 0.0        # kill residual noise in gap / outer area
# keep the glow gradient as-is; snap the opaque plateau to 255
template[template >= 254.5] = 255.0
template = np.clip(np.round(template), 0, 255).astype(np.uint8)

# Content mask = fully opaque region (where the portrait is placed)
content_mask = (template == 255)

# Glow mask = partially transparent, non-zero, non-content (the black halo)
glow_mask = (template > 0) & (~content_mask)

# Report geometry
ys, xs = np.where(content_mask)
print(f"Template size: {W}x{H}")
print(f"Content bbox: x[{xs.min()}..{xs.max()}] y[{ys.min()}..{ys.max()}]")
print(f"Content pixels: {content_mask.sum()}  ({100*content_mask.mean():.1f}% of frame)")
print(f"Glow pixels:    {glow_mask.sum()}  ({100*glow_mask.mean():.1f}% of frame)")
print(f"Glow alpha range: {template[glow_mask].min()}..{template[glow_mask].max()}")

# Save artifacts
np.save(os.path.join(BASE, "template_alpha.npy"), template)
Image.fromarray(template, mode="L").save(os.path.join(BASE, "template_alpha.png"))
# Visualization: black glow + white content over checker
vis = np.zeros((H, W, 4), dtype=np.uint8)
vis[..., 3] = template
vis[content_mask, :3] = 255           # content shown white
# glow stays black rgb
Image.fromarray(vis, mode="RGBA").save(os.path.join(BASE, "template_preview.png"))
print("\nSaved template_alpha.npy, template_alpha.png, template_preview.png")
