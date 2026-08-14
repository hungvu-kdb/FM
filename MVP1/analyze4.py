"""Understand color content of glow region and build canonical mask."""
import os, glob
import numpy as np
from PIL import Image

BASE = os.path.dirname(__file__)
ROOT = os.path.join(BASE, "Root")
files = sorted(glob.glob(os.path.join(ROOT, "*.png")))

# Look at glow-region RGB for several images at y=155, x=0..9
print("Glow-region RGB (premultiplied look) at y=155, x=3..9:")
for f in files[:6]:
    im = np.asarray(Image.open(f).convert("RGBA"))
    row = im[155]
    # compare glow pixel color vs nearest content pixel color (x=20)
    content = row[20, :3]
    print(f"\n{os.path.basename(f)}: content@x20 RGB={content.tolist()}")
    for x in [3,5,7,9]:
        px = row[x]
        print(f"   x={x}: RGB={px[:3].tolist()} A={px[3]}")

# Is the glow color ~ constant (a fixed halo color) or does it track content?
# Compute, per image, the mean glow RGB (alpha 10..100) vs mean content edge RGB.
print("\n\n--- Per-image: glow color vs content-edge color ---")
mean_alpha = np.load(os.path.join(BASE, "mean_alpha.npy"))
glow_mask = (mean_alpha > 5) & (mean_alpha < 150)
content_mask = mean_alpha >= 254.5
# erode content edge: pixels adjacent to gap
for f in files[:8]:
    im = np.asarray(Image.open(f).convert("RGBA")).astype(np.float64)
    rgb = im[:, :, :3]
    a = im[:, :, 3]
    g = glow_mask & (a > 5)
    if g.sum() > 0:
        glow_rgb = rgb[g].mean(axis=0)
    else:
        glow_rgb = [0,0,0]
    c = content_mask
    content_rgb = rgb[c].mean(axis=0)
    print(f"{os.path.basename(f):13s} glow_mean_RGB={np.round(glow_rgb,1).tolist()}  content_mean_RGB={np.round(content_rgb,1).tolist()}")
