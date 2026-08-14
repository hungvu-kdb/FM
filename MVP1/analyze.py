"""Analyze the common pattern among portrait images in Root folder."""
import os
import glob
import numpy as np
from PIL import Image

ROOT = os.path.join(os.path.dirname(__file__), "Root")

files = sorted(glob.glob(os.path.join(ROOT, "*.png")))
print(f"Found {len(files)} images\n")

alphas = []
sizes = set()
modes = set()

for f in files:
    im = Image.open(f)
    modes.add(im.mode)
    sizes.add(im.size)
    im = im.convert("RGBA")
    arr = np.asarray(im).astype(np.float64)
    alphas.append(arr[:, :, 3])
    print(f"{os.path.basename(f):15s} size={im.size} mode={Image.open(f).mode}")

print("\nAll sizes:", sizes)
print("All modes:", modes)

# Stack alpha channels
A = np.stack(alphas, axis=0)  # (N, H, W)
N, H, W = A.shape
print(f"\nAlpha stack shape: {A.shape}")

mean_alpha = A.mean(axis=0)
std_alpha = A.std(axis=0)

print(f"\nAlpha value range across all: min={A.min()}, max={A.max()}")
print(f"Mean alpha: min={mean_alpha.min():.2f}, max={mean_alpha.max():.2f}")
print(f"Std alpha (pixel-wise across images): mean={std_alpha.mean():.2f}, max={std_alpha.max():.2f}")

# How consistent is the alpha mask across images? Low std => it's a fixed mask/border
print(f"\nFraction of pixels with std < 5 (nearly identical across imgs): {(std_alpha < 5).mean():.4f}")
print(f"Fraction of pixels with std < 1: {(std_alpha < 1).mean():.4f}")

# Examine the border: look at alpha along edges and center
print("\n--- Mean alpha map sampled ---")
# corners
print("corners (mean alpha):",
      mean_alpha[0,0], mean_alpha[0,-1], mean_alpha[-1,0], mean_alpha[-1,-1])
print("center (mean alpha):", mean_alpha[H//2, W//2])

# Row profile down the vertical center
print("\nVertical center-column alpha profile (every 20px):")
for y in range(0, H, 20):
    print(f"  y={y:3d}: {mean_alpha[y, W//2]:.1f}")

print("\nHorizontal center-row alpha profile (every 20px):")
for x in range(0, W, 20):
    print(f"  x={x:3d}: {mean_alpha[H//2, x]:.1f}")

# Save mean alpha as an image for inspection
Image.fromarray(mean_alpha.astype(np.uint8)).save(os.path.join(os.path.dirname(__file__), "mean_alpha.png"))
Image.fromarray((std_alpha).astype(np.uint8)).save(os.path.join(os.path.dirname(__file__), "std_alpha.png"))
np.save(os.path.join(os.path.dirname(__file__), "mean_alpha.npy"), mean_alpha)
print("\nSaved mean_alpha.png, std_alpha.png, mean_alpha.npy")
