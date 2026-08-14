"""Full-resolution look at the edge structure."""
import os
import numpy as np
from PIL import Image

BASE = os.path.dirname(__file__)
mean_alpha = np.load(os.path.join(BASE, "mean_alpha.npy"))
H, W = mean_alpha.shape

y = 155
print(f"Full row y={y} alpha, x=0..40:")
print(" ".join(f"{int(mean_alpha[y,x]):3d}" for x in range(0,41)))
print(f"\nFull row y={y} alpha, x=220..259:")
print(" ".join(f"{int(mean_alpha[y,x]):3d}" for x in range(220,260)))

x = 130
print(f"\nFull col x={x} alpha, y=0..40:")
print(" ".join(f"{int(mean_alpha[y2,x]):3d}" for y2 in range(0,41)))
print(f"\nFull col x={x} alpha, y=270..309:")
print(" ".join(f"{int(mean_alpha[y2,x]):3d}" for y2 in range(270,310)))

# Check a raw image (RGBA) to see if same double-edge appears
raw = Image.open(os.path.join(BASE, "Root", "1000050.png")).convert("RGBA")
rarr = np.asarray(raw)
print(f"\nRaw image 1000050 row y=155 alpha x=0..40:")
print(" ".join(f"{int(rarr[155,x,3]):3d}" for x in range(0,41)))

# Histogram of interior alpha values
interior = mean_alpha[30:280, 30:230]
print(f"\nInterior region (30:280,30:230) alpha: min={interior.min()}, max={interior.max()}, mean={interior.mean():.2f}")

# Where exactly does alpha reach >=255 (first from left at y=155)?
row = mean_alpha[155]
print("\nx where alpha jumps at y=155:")
for x in range(8, 22):
    print(f"  x={x}: {mean_alpha[155,x]:.1f}")
