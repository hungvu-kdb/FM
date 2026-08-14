/**
 * MVP3 Step 2 — apply the separable frame to your own portrait.
 *
 *   node MVP3/apply-frame.mjs INPUT [OUTPUT] [--model FILE] [--fit] [--no-resize]
 *
 * Composite. The source alpha is first normalised against the frame it may
 * already carry, so re-applying the frame is a no-op:
 *
 *   A_content(y,x) = clamp( 255 · A_src(y,x) / A_model(y,x), 0, 255 )
 *   A_out(y,x)     = A_model(y,x) · A_content(y,x) / 255
 *   RGB_out        = RGB_src where the model is opaque enough to show content,
 *                    (0,0,0) elsewhere so the halo reads as a black glow.
 *
 * A fully opaque input gives A_out = A_model exactly; a fully transparent input
 * stays transparent; a soft cut-out keeps its own gradient.
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { basename, dirname, extname, join, resolve } from "node:path";
import { decodePng, encodeRgbaPng } from "./png.mjs";
import { renderAlpha } from "./separable.mjs";

const HERE = import.meta.dirname;
const DEFAULT_MODEL = join(HERE, "model.json");
const CONTENT_THRESHOLD = 128; // alpha at/above this is treated as portrait content

function parseArgs(argv) {
  const options = { input: null, output: null, model: DEFAULT_MODEL, fit: false, resize: true };
  const positional = [];
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--model") options.model = resolve(argv[(i += 1)]);
    else if (arg === "--fit") options.fit = true;
    else if (arg === "--no-resize") options.resize = false;
    else if (arg.startsWith("--")) throw new Error(`unknown option ${arg}`);
    else positional.push(arg);
  }
  if (positional.length === 0) throw new Error("usage: node apply-frame.mjs INPUT [OUTPUT] [--fit] [--no-resize]");
  options.input = resolve(positional[0]);
  options.output = positional[1]
    ? resolve(positional[1])
    : join(dirname(options.input), `${basename(options.input, extname(options.input))}_mvp3.png`);
  return options;
}

function loadModel(path) {
  if (!existsSync(path)) throw new Error(`model not found: ${path}; run analyze.mjs first`);
  const model = JSON.parse(readFileSync(path, "utf8"));
  if (!Array.isArray(model.terms) || model.terms.length === 0) throw new Error("model has no separable terms");
  for (const term of model.terms) {
    if (term.rows.length !== model.height || term.cols.length !== model.width) {
      throw new Error("model term profile lengths do not match the model dimensions");
    }
  }
  return model;
}

/** Bilinear resample of straight RGBA to an exact target size. */
function resampleBilinear(src, srcW, srcH, dstW, dstH) {
  if (srcW === dstW && srcH === dstH) return src;
  const out = new Uint8Array(dstW * dstH * 4);
  const scaleX = srcW / dstW;
  const scaleY = srcH / dstH;
  for (let y = 0; y < dstH; y += 1) {
    const fy = Math.min(srcH - 1, Math.max(0, (y + 0.5) * scaleY - 0.5));
    const y0 = Math.floor(fy);
    const y1 = Math.min(srcH - 1, y0 + 1);
    const wy = fy - y0;
    for (let x = 0; x < dstW; x += 1) {
      const fx = Math.min(srcW - 1, Math.max(0, (x + 0.5) * scaleX - 0.5));
      const x0 = Math.floor(fx);
      const x1 = Math.min(srcW - 1, x0 + 1);
      const wx = fx - x0;
      const i00 = (y0 * srcW + x0) * 4;
      const i01 = (y0 * srcW + x1) * 4;
      const i10 = (y1 * srcW + x0) * 4;
      const i11 = (y1 * srcW + x1) * 4;
      const d = (y * dstW + x) * 4;
      for (let c = 0; c < 4; c += 1) {
        const top = src[i00 + c] * (1 - wx) + src[i01 + c] * wx;
        const bottom = src[i10 + c] * (1 - wx) + src[i11 + c] * wx;
        out[d + c] = Math.round(top * (1 - wy) + bottom * wy);
      }
    }
  }
  return out;
}

/** Scale-to-cover then centre-crop, so the rounded corners never eat the subject. */
function coverCrop(src, srcW, srcH, dstW, dstH) {
  const scale = Math.max(dstW / srcW, dstH / srcH);
  const midW = Math.max(1, Math.round(srcW * scale));
  const midH = Math.max(1, Math.round(srcH * scale));
  const scaled = resampleBilinear(src, srcW, srcH, midW, midH);
  const left = Math.floor((midW - dstW) / 2);
  const top = Math.floor((midH - dstH) / 2);
  const out = new Uint8Array(dstW * dstH * 4);
  for (let y = 0; y < dstH; y += 1) {
    const from = ((y + top) * midW + left) * 4;
    out.set(scaled.subarray(from, from + dstW * 4), y * dstW * 4);
  }
  return out;
}

export function applyFrame(image, model, { fit = false, resize = true } = {}) {
  const { width, height } = model;
  let pixels = image.data;
  if (image.width !== width || image.height !== height) {
    if (!resize) throw new Error(`input must be ${width}x${height}; got ${image.width}x${image.height}`);
    pixels = fit
      ? coverCrop(image.data, image.width, image.height, width, height)
      : resampleBilinear(image.data, image.width, image.height, width, height);
  } else if (fit) {
    pixels = coverCrop(image.data, width, height, width, height);
  }

  const frame = renderAlpha(model);
  const out = new Uint8Array(width * height * 4);
  for (let i = 0, n = width * height; i < n; i += 1) {
    const d = i * 4;
    const frameAlpha = frame[i];
    if (frameAlpha >= CONTENT_THRESHOLD) {
      out[d] = pixels[d];
      out[d + 1] = pixels[d + 1];
      out[d + 2] = pixels[d + 2];
    } // else leave RGB at black: that is the glow colour measured in every sample
    // Undo any frame alpha the input already carries, then re-apply this frame.
    const content = frameAlpha > 0 ? Math.min(255, (pixels[d + 3] * 255) / frameAlpha) : 0;
    out[d + 3] = Math.round((frameAlpha * content) / 255);
  }
  return { width, height, data: out };
}

function main() {
  let options;
  try {
    options = parseArgs(process.argv.slice(2));
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
    return;
  }
  const model = loadModel(options.model);
  const image = decodePng(readFileSync(options.input));
  const result = applyFrame(image, model, { fit: options.fit, resize: options.resize });
  mkdirSync(dirname(options.output), { recursive: true });
  writeFileSync(options.output, encodeRgbaPng(result.width, result.height, result.data));
  console.log(`Saved ${options.output} (${result.width}x${result.height}, RGBA, rank=${model.rank}, fit=${options.fit})`);
}

if (process.argv[1] && resolve(process.argv[1]) === resolve(import.meta.filename)) main();
