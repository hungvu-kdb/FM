/**
 * MVP3 validation — no test framework, just assertions over real data.
 *
 *   node MVP3/verify.mjs
 */
import assert from "node:assert/strict";
import { readFileSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { decodePng, encodeRgbaPng, encodeGrayPng } from "./png.mjs";
import { applyFrame } from "./apply-frame.mjs";
import { renderAlpha, toBytes } from "./separable.mjs";

const HERE = import.meta.dirname;
const ROOT = resolve(HERE, "..");
const checks = [];

function check(name, fn) {
  try {
    const detail = fn();
    checks.push({ name, ok: true, detail });
    console.log(`PASS  ${name}${detail ? ` — ${detail}` : ""}`);
  } catch (error) {
    checks.push({ name, ok: false, detail: error.message });
    console.error(`FAIL  ${name} — ${error.message}`);
  }
}

const model = JSON.parse(readFileSync(join(HERE, "model.json"), "utf8"));
const frame = renderAlpha(model);

check("model is separable rank-k only (no 2-D matrix stored)", () => {
  assert.equal(model.width, 260);
  assert.equal(model.height, 310);
  assert.ok(model.terms.length >= 1);
  for (const term of model.terms) {
    assert.equal(typeof term.weight, "number");
    assert.equal(term.rows.length, model.height);
    assert.equal(term.cols.length, model.width);
  }
  const stored = model.terms.length * (model.width + model.height + 1);
  const dense = model.width * model.height;
  return `${stored} numbers vs ${dense} for a dense matrix (${(stored / dense * 100).toFixed(1)}%)`;
});

check("PNG codec round-trips RGBA losslessly", () => {
  const width = 37;
  const height = 19;
  const data = new Uint8Array(width * height * 4);
  for (let i = 0; i < data.length; i += 1) data[i] = (i * 37 + 11) & 0xff;
  const decoded = decodePng(encodeRgbaPng(width, height, data));
  assert.equal(decoded.width, width);
  assert.equal(decoded.height, height);
  assert.deepEqual(Array.from(decoded.data), Array.from(data));
  return `${width}x${height} exact`;
});

check("PNG codec round-trips greyscale losslessly", () => {
  const gray = new Uint8Array(64);
  for (let i = 0; i < gray.length; i += 1) gray[i] = (i * 4) & 0xff;
  const decoded = decodePng(encodeGrayPng(8, 8, gray));
  for (let i = 0; i < gray.length; i += 1) assert.equal(decoded.data[i * 4], gray[i]);
  return "8x8 exact";
});

check("rendered frame reproduces real Root samples", () => {
  const names = ["1000050.png", "100013.png", "1002273.png"];
  const summary = [];
  for (const name of names) {
    const image = decodePng(readFileSync(join(ROOT, "Root", name)));
    let sum = 0;
    let within3 = 0;
    for (let i = 0; i < frame.length; i += 1) {
      const error = Math.abs(frame[i] - image.data[i * 4 + 3]);
      sum += error;
      if (error <= 3) within3 += 1;
    }
    const mae = sum / frame.length;
    const pct = (within3 / frame.length) * 100;
    assert.ok(mae < 2, `${name} MAE ${mae.toFixed(3)} is too high`);
    assert.ok(pct > 95, `${name} only ${pct.toFixed(1)}% within ±3`);
    summary.push(`${name} MAE=${mae.toFixed(3)} ${pct.toFixed(1)}% within ±3`);
  }
  return summary.join("; ");
});

check("apply output is 260x310 RGBA and decodes cleanly", () => {
  const source = decodePng(readFileSync(join(ROOT, "Test", "alavez.png")));
  const result = applyFrame(source, model, { resize: true });
  const decoded = decodePng(encodeRgbaPng(result.width, result.height, result.data));
  assert.equal(decoded.width, 260);
  assert.equal(decoded.height, 310);
  return `source ${source.width}x${source.height} -> 260x310`;
});

check("halo pixels are black and the centre stays opaque", () => {
  const source = decodePng(readFileSync(join(ROOT, "Test", "alavez.png")));
  const result = applyFrame(source, model, { resize: true });
  const at = (x, y) => {
    const d = (y * 260 + x) * 4;
    return [result.data[d], result.data[d + 1], result.data[d + 2], result.data[d + 3]];
  };
  const corner = at(2, 2);
  assert.deepEqual(corner.slice(0, 3), [0, 0, 0], "outer glow must be pure black");
  const centre = at(130, 155);
  assert.ok(centre[3] > 250, `centre alpha ${centre[3]} should be opaque`);
  return `corner rgb=(0,0,0) a=${corner[3]}, centre a=${centre[3]}`;
});

check("transformation is idempotent", () => {
  const source = decodePng(readFileSync(join(ROOT, "Test", "alavez.png")));
  const once = applyFrame(source, model, { resize: true });
  const twice = applyFrame(once, model, { resize: true });
  let maxDelta = 0;
  for (let i = 0; i < once.data.length; i += 1) {
    maxDelta = Math.max(maxDelta, Math.abs(once.data[i] - twice.data[i]));
  }
  assert.ok(maxDelta <= 1, `re-applying changed pixels by up to ${maxDelta}`);
  return `max channel delta on re-apply = ${maxDelta}`;
});

check("source transparency is respected", () => {
  const width = model.width;
  const height = model.height;
  const data = new Uint8Array(width * height * 4);
  for (let i = 0; i < width * height; i += 1) {
    data[i * 4] = 200;
    data[i * 4 + 1] = 100;
    data[i * 4 + 2] = 50;
    data[i * 4 + 3] = 0; // fully transparent input
  }
  const result = applyFrame({ width, height, data }, model);
  const maxAlpha = result.data.reduce((max, value, index) => (index % 4 === 3 ? Math.max(max, value) : max), 0);
  assert.equal(maxAlpha, 0);
  return "fully transparent input yields fully transparent output";
});

const failed = checks.filter((c) => !c.ok);
writeFileSync(
  join(HERE, "verification.json"),
  `${JSON.stringify({ generatedAt: new Date().toISOString(), runtime: process.version, checks, failed: failed.length }, null, 2)}\n`,
);
console.log(`\n${checks.length - failed.length}/${checks.length} checks passed`);
process.exitCode = failed.length === 0 ? 0 : 1;
