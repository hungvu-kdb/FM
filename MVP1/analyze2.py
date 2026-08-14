"""Characterize the border mask geometry and gradient precisely."""
import os
import numpy as np
from PIL import Image

BASE = os.path.dirname(__file__)
mean_alpha = np.load(os.path.join(BASE, "mean_alpha.npy"))
H, W = mean_alpha.shape
print(f"Mask shape: H={H}, W={W}")

# Threshold to find where content becomes fully opaque (255)
full = mean_alpha >= 254.5

# For each row, find first and last fully-opaque column
print("\n--- Border width per edge (first fully-opaque pixel) ---")
def first_last(mask_row):
    idx = np.where(mask_row)[0]
    if len(idx) == 0:
        return None, None
    return idx[0], idx[-1]

# Sample rows
print("Row : left_opaque right_opaque")
for y in [0,1,2,3,4,5,10,20,50,150,300,305,308,309]:
    l, r = first_last(full[y])
    print(f"  y={y:3d}: left={l} right={r}")

print("\nCol : top_opaque bottom_opaque")
for x in [0,1,2,3,4,5,10,20,50,130,255,258,259]:
    idx = np.where(full[:, x])[0]
    if len(idx):
        print(f"  x={x:3d}: top={idx[0]} bottom={idx[-1]}")
    else:
        print(f"  x={x:3d}: none")

# Examine top-left corner region gradient in detail (0..15)
print("\n--- Top-left 16x16 corner mean alpha ---")
for y in range(16):
    row = " ".join(f"{int(mean_alpha[y,x]):3d}" for x in range(16))
    print(f"y={y:2d}: {row}")

# Vertical edge transition (left edge) at a middle row
print("\n--- Left-edge alpha transition at y=155 (x=0..12) ---")
print(" ".join(f"{int(mean_alpha[155,x]):3d}" for x in range(13)))
print("--- Right-edge alpha transition at y=155 (x=247..259) ---")
print(" ".join(f"{int(mean_alpha[155,x]):3d}" for x in range(247,260)))
print("--- Top-edge alpha transition at x=130 (y=0..12) ---")
print(" ".join(f"{int(mean_alpha[y,130]):3d}" for y in range(13)))
print("--- Bottom-edge alpha transition at x=130 (y=297..309) ---")
print(" ".join(f"{int(mean_alpha[y,130]):3d}" for y in range(297,310)))

# Count distinct alpha "plateaus" - is border uniform width?
# Detect corner radius: find where the opaque region starts on the very top rows
print("\n--- Opaque span width by row (top rows, corner rounding) ---")
for y in range(0, 20):
    l, r = first_last(full[y])
    if l is not None:
        print(f"  y={y:2d}: opaque x in [{l},{r}], inset_left={l}, inset_right={W-1-r}")
    else:
        print(f"  y={y:2d}: no opaque pixels")
