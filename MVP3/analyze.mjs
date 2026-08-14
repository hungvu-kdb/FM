/**
 * MVP3 Step 1 — analyse Root/*.png and fit a separable low-rank alpha model.
 *
 *   node MVP3/analyze.mjs [--rank K] [--root DIR]
 *
 * Writes model.json, analysis_report.json and generated_alpha.png into MVP3/.
 */
import { readdirSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { decodePng, encodeGrayPng } from "./png.mjs";
import { deflate, extractRankOneTerm, renderAlpha, toBytes } from "./separable.mjs";

const HERE = import.meta.dirname;
const ROOT = resolve(HERE, "..");
const MAX_RANK = 24;

function parseArgs(argv) {
  const options = { rank: 8, root: join(ROOT, "Root") };
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === "--rank") options.rank = Number.parseInt(argv[i + 1], 10), (i += 1);
    else if (argv[i] === "--root") options.root = resolve(argv[i + 1]), (i += 1);
    else throw new Error(`unknown argument ${argv[i]}`);
  }
  if (!Number.isInteger(options.rank) || options.rank < 1 || options.rank > MAX_RANK) {
    throw new Error(`--rank must be an integer in 1..${MAX_RANK}`);
  }
  return options;
}

function loadAlphaFields(dir) {
  const files = readdirSync(dir).filter((name) => name.toLowerCase().endsWith(".png")).sort();
  if (files.length === 0) throw new Error(`no PNG samples found in ${dir}`);
  const samples = [];
  let width = 0;
  let height = 0;
  for (const name of files) {
    const image = decodePng(readFileSync(join(dir, name)));
    if (width === 0) ({ width, height } = image);
    if (image.width !== width || image.height !== height) {
      throw new Error(`${name} is ${image.width}x${image.height}; expected ${width}x${height}`);
    }
    const alpha = new Float64Array(width * height);
    for (let i = 0; i < alpha.length; i += 1) alpha[i] = image.data[i * 4 + 3];
    samples.push({ name, alpha, colorType: image.sourceColorType });
  }
  return { width, height, samples };
}

function meanField(samples, length) {
  const mean = new Float64Array(length);
  for (const { alpha } of samples) for (let i = 0; i < length; i += 1) mean[i] += alpha[i];
  for (let i = 0; i < length; i += 1) mean[i] /= samples.length;
  return mean;
}

function errorStats(actual, expected) {
  const errors = new Float64Array(actual.length);
  let sum = 0;
  let max = 0;
  for (let i = 0; i < actual.length; i += 1) {
    const e = Math.abs(actual[i] - expected[i]);
    errors[i] = e;
    sum += e;
    if (e > max) max = e;
  }
  errors.sort();
  const at = (q) => errors[Math.min(errors.length - 1, Math.floor(q * errors.length))];
  return { mae: sum / actual.length, max, p50: at(0.5), p90: at(0.9), p99: at(0.99) };
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  const { width, height, samples } = loadAlphaFields(options.root);
  const length = width * height;
  console.log(`Loaded ${samples.length} samples at ${width}x${height} from ${options.root}`);

  // Cross-image agreement: is a single shared alpha field even justified?
  const mean = meanField(samples, length);
  let stdSum = 0;
  let stdMax = 0;
  for (let i = 0; i < length; i += 1) {
    let variance = 0;
    for (const { alpha } of samples) variance += (alpha[i] - mean[i]) ** 2;
    const std = Math.sqrt(variance / samples.length);
    stdSum += std;
    if (std > stdMax) stdMax = std;
  }

  // Fit the separable terms against the mean field via deflation.
  const residual = Float64Array.from(mean);
  const terms = [];
  const spectrum = [];
  for (let k = 0; k < options.rank; k += 1) {
    const term = extractRankOneTerm(residual, width, height);
    if (!term) break;
    deflate(residual, width, height, term);
    terms.push(term);
    const partial = renderAlpha({ width, height, terms });
    const stats = errorStats(partial, mean);
    spectrum.push({ rank: terms.length, weight: term.weight, maeVsMean: stats.mae });
    console.log(`  rank ${String(terms.length).padStart(2)}  weight=${term.weight.toFixed(3).padStart(12)}  MAE vs mean=${stats.mae.toFixed(4)}`);
  }

  const model = {
    schema: "mvp3-separable-alpha/1",
    width,
    height,
    rank: terms.length,
    generatedFrom: { sampleCount: samples.length, directory: "Root" },
    terms: terms.map(({ weight, rows, cols }) => ({
      weight: Number(weight.toFixed(9)),
      rows: rows.map((v) => Number(v.toFixed(9))),
      cols: cols.map((v) => Number(v.toFixed(9))),
    })),
  };

  const rendered = renderAlpha(model);
  const perSample = samples.map(({ name, alpha, colorType }) => ({
    name,
    colorType,
    ...errorStats(rendered, alpha),
  }));
  const maes = perSample.map((s) => s.mae).sort((a, b) => a - b);
  const globalStats = errorStats(rendered, mean);

  const report = {
    generatedAt: new Date().toISOString(),
    runtime: `Node.js ${process.version} (no third-party packages)`,
    dimensions: { width, height },
    sampleCount: samples.length,
    crossImageAgreement: { meanStd: stdSum / length, maxStd: stdMax },
    rank: terms.length,
    spectrum,
    vsMeanField: globalStats,
    perSampleMae: {
      min: maes[0],
      median: maes[Math.floor(maes.length / 2)],
      max: maes[maes.length - 1],
      mean: maes.reduce((a, b) => a + b, 0) / maes.length,
    },
    perSample,
  };

  mkdirSync(HERE, { recursive: true });
  writeFileSync(join(HERE, "model.json"), `${JSON.stringify(model, null, 2)}\n`);
  writeFileSync(join(HERE, "analysis_report.json"), `${JSON.stringify(report, null, 2)}\n`);
  writeFileSync(join(HERE, "generated_alpha.png"), encodeGrayPng(width, height, toBytes(rendered)));

  console.log(`Cross-image alpha std: mean=${report.crossImageAgreement.meanStd.toFixed(4)} max=${stdMax.toFixed(2)}`);
  console.log(`Rank-${terms.length} model MAE vs mean field: ${globalStats.mae.toFixed(4)}`);
  console.log(`Per-sample MAE median: ${report.perSampleMae.median.toFixed(4)}`);
  console.log(`Wrote model.json, analysis_report.json, generated_alpha.png in ${dirname(join(HERE, "model.json"))}`);
}

main();
