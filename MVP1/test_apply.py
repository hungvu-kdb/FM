"""Test apply_border by generating a portrait and verifying output vs template."""
import os
import numpy as np
from PIL import Image
from apply_border import apply_border, load_template, TARGET_SIZE

BASE = os.path.dirname(os.path.abspath(__file__))
template = load_template()
H, W = template.shape

# 1) Make a synthetic gradient portrait (so we can see content survives)
xv, yv = np.meshgrid(np.linspace(0, 255, W), np.linspace(0, 255, H))
r = xv.astype(np.uint8)
g = yv.astype(np.uint8)
b = ((xv + yv) / 2).astype(np.uint8)
portrait = Image.fromarray(np.dstack([r, g, b]).astype(np.uint8), "RGB")
portrait.save(os.path.join(BASE, "test_input.png"))

# 2) Apply (default + fit)
out = apply_border(portrait, template, fit=False)
out.save(os.path.join(BASE, "test_output.png"))
out_fit = apply_border(portrait, template, fit=True)
out_fit.save(os.path.join(BASE, "test_output_fit.png"))

# 3) Verify: output alpha == template exactly
oarr = np.asarray(out)
assert np.array_equal(oarr[:, :, 3], template), "Alpha mismatch!"
print("PASS: output alpha channel matches template exactly.")

# 4) Verify: outside content region RGB is black
content_mask = template == 255
outside_rgb = oarr[~content_mask][:, :3]
assert outside_rgb.max() == 0, "Non-black pixel outside content!"
print("PASS: all pixels outside content region are black.")

# 5) Verify: inside content region matches portrait
parr = np.asarray(portrait)
assert np.array_equal(oarr[content_mask][:, :3], parr[content_mask]), "Content changed!"
print("PASS: content region preserves portrait pixels.")

# 6) Compare output alpha to a REAL sample's alpha (should be near-identical)
real = np.asarray(Image.open(os.path.join(BASE, "Root", "1000050.png")).convert("RGBA"))[:, :, 3]
diff = np.abs(real.astype(int) - template.astype(int))
print(f"Alpha diff vs real sample 1000050: mean={diff.mean():.2f}, max={diff.max()}, "
      f"%pixels within 3 = {100*(diff<=3).mean():.2f}%")

# 7) Round-trip on a real portrait: strip a sample to RGB, re-apply, compare alpha
sample = Image.open(os.path.join(BASE, "Root", "100013.png")).convert("RGBA")
sarr = np.asarray(sample)
# reconstruct an opaque RGB portrait from its content
rgb_only = Image.fromarray(sarr[:, :, :3], "RGB")
re = apply_border(rgb_only, template, fit=False)
rediff = np.abs(np.asarray(re)[:, :, 3].astype(int) - sarr[:, :, 3].astype(int))
print(f"Re-applied alpha vs original 100013: mean={rediff.mean():.2f}, max={rediff.max()}, "
      f"%within3={100*(rediff<=3).mean():.2f}%")

print("\nAll tests passed.")
