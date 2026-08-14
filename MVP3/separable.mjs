/**
 * MVP3 model: the alpha field as a low-rank SEPARABLE factorization.
 *
 *   A(y, x) ≈ clamp( Σ_{k=1..K} s_k · u_k(y) · v_k(x) , 0, 255 )
 *
 * The stored model is a list of rank-1 terms, each holding one column profile
 * v_k (length W) and one row profile u_k (length H) plus a scalar weight s_k.
 * No 2-D per-pixel matrix and no geometric distance field are stored.
 */

/** Rebuild the H×W alpha field from the separable terms. */
export function renderAlpha(model) {
  const { width, height, terms } = model;
  const alpha = new Float64Array(width * height);
  for (const { weight, rows, cols } of terms) {
    for (let y = 0; y < height; y += 1) {
      const scaled = weight * rows[y];
      if (scaled === 0) continue;
      const base = y * width;
      for (let x = 0; x < width; x += 1) alpha[base + x] += scaled * cols[x];
    }
  }
  for (let i = 0; i < alpha.length; i += 1) alpha[i] = Math.min(255, Math.max(0, alpha[i]));
  return alpha;
}

/** Quantise a rendered alpha field to bytes. */
export function toBytes(alpha) {
  const out = new Uint8Array(alpha.length);
  for (let i = 0; i < alpha.length; i += 1) out[i] = Math.round(alpha[i]);
  return out;
}

/**
 * Rank-1 term extraction by alternating power iteration (the same fixed point
 * an SVD converges to, without needing a full linear-algebra library).
 */
export function extractRankOneTerm(matrix, width, height, iterations = 120) {
  let cols = new Float64Array(width).fill(1 / Math.sqrt(width));
  let rows = new Float64Array(height);
  for (let iteration = 0; iteration < iterations; iteration += 1) {
    // rows <- matrix · cols
    rows.fill(0);
    for (let y = 0; y < height; y += 1) {
      const base = y * width;
      let sum = 0;
      for (let x = 0; x < width; x += 1) sum += matrix[base + x] * cols[x];
      rows[y] = sum;
    }
    const rowNorm = norm(rows);
    if (rowNorm === 0) return null;
    scale(rows, 1 / rowNorm);

    // cols <- matrixᵀ · rows
    const next = new Float64Array(width);
    for (let y = 0; y < height; y += 1) {
      const base = y * width;
      const r = rows[y];
      if (r === 0) continue;
      for (let x = 0; x < width; x += 1) next[x] += matrix[base + x] * r;
    }
    const colNorm = norm(next);
    if (colNorm === 0) return null;
    scale(next, 1 / colNorm);
    cols = next;
  }

  // weight = uᵀ A v, the singular value for these unit profiles
  let weight = 0;
  for (let y = 0; y < height; y += 1) {
    const base = y * width;
    let sum = 0;
    for (let x = 0; x < width; x += 1) sum += matrix[base + x] * cols[x];
    weight += rows[y] * sum;
  }
  return { weight, rows: Array.from(rows), cols: Array.from(cols) };
}

/** Subtract a rank-1 term from the matrix (deflation) so the next term sees the residual. */
export function deflate(matrix, width, height, term) {
  for (let y = 0; y < height; y += 1) {
    const scaled = term.weight * term.rows[y];
    const base = y * width;
    for (let x = 0; x < width; x += 1) matrix[base + x] -= scaled * term.cols[x];
  }
}

function norm(vector) {
  let sum = 0;
  for (let i = 0; i < vector.length; i += 1) sum += vector[i] * vector[i];
  return Math.sqrt(sum);
}

function scale(vector, factor) {
  for (let i = 0; i < vector.length; i += 1) vector[i] *= factor;
}
