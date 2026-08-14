/**
 * Zero-dependency PNG reader/writer for MVP3.
 *
 * Only what this project actually needs:
 *   decode: 8-bit non-interlaced, colour type 3 (palette + optional tRNS)
 *           and colour type 6 (RGBA), plus 0 (grey) and 2 (RGB).
 *   encode: 8-bit RGBA and 8-bit greyscale, filter 0, non-interlaced.
 *
 * Node's built-in `zlib` supplies the DEFLATE codec, so no npm package is used.
 */
import { deflateSync, inflateSync } from "node:zlib";

const SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

const CRC_TABLE = (() => {
  const table = new Int32Array(256);
  for (let n = 0; n < 256; n += 1) {
    let c = n;
    for (let k = 0; k < 8; k += 1) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    table[n] = c;
  }
  return table;
})();

function crc32(buf) {
  let c = 0xffffffff;
  for (let i = 0; i < buf.length; i += 1) c = CRC_TABLE[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

function paethPredictor(a, b, c) {
  const p = a + b - c;
  const pa = Math.abs(p - a);
  const pb = Math.abs(p - b);
  const pc = Math.abs(p - c);
  if (pa <= pb && pa <= pc) return a;
  return pb <= pc ? b : c;
}

/** Reverse the five PNG scanline filters in place, returning packed samples. */
function unfilter(raw, width, height, bytesPerPixel) {
  const stride = width * bytesPerPixel;
  const out = Buffer.alloc(stride * height);
  let pos = 0;
  for (let y = 0; y < height; y += 1) {
    const filter = raw[pos];
    pos += 1;
    const line = raw.subarray(pos, pos + stride);
    pos += stride;
    const cur = out.subarray(y * stride, (y + 1) * stride);
    const prev = y > 0 ? out.subarray((y - 1) * stride, y * stride) : null;
    for (let i = 0; i < stride; i += 1) {
      const x = line[i];
      const a = i >= bytesPerPixel ? cur[i - bytesPerPixel] : 0;
      const b = prev ? prev[i] : 0;
      const c = prev && i >= bytesPerPixel ? prev[i - bytesPerPixel] : 0;
      let value;
      switch (filter) {
        case 0: value = x; break;
        case 1: value = x + a; break;
        case 2: value = x + b; break;
        case 3: value = x + ((a + b) >> 1); break;
        case 4: value = x + paethPredictor(a, b, c); break;
        default: throw new Error(`unsupported PNG filter type ${filter} on row ${y}`);
      }
      cur[i] = value & 0xff;
    }
  }
  return out;
}

/**
 * Decode a PNG buffer to straight (non-premultiplied) RGBA.
 * @returns {{width: number, height: number, data: Uint8Array, sourceColorType: number}}
 */
export function decodePng(buffer) {
  if (!buffer.subarray(0, 8).equals(SIGNATURE)) throw new Error("not a PNG file");

  let width = 0;
  let height = 0;
  let depth = 0;
  let colorType = 0;
  let interlace = 0;
  let palette = null;
  let paletteAlpha = null;
  const idat = [];

  let offset = 8;
  while (offset + 8 <= buffer.length) {
    const length = buffer.readUInt32BE(offset);
    const type = buffer.toString("latin1", offset + 4, offset + 8);
    const body = buffer.subarray(offset + 8, offset + 8 + length);
    if (type === "IHDR") {
      width = body.readUInt32BE(0);
      height = body.readUInt32BE(4);
      depth = body[8];
      colorType = body[9];
      interlace = body[12];
    } else if (type === "PLTE") {
      palette = Buffer.from(body);
    } else if (type === "tRNS") {
      paletteAlpha = Buffer.from(body);
    } else if (type === "IDAT") {
      idat.push(Buffer.from(body));
    } else if (type === "IEND") {
      break;
    }
    offset += 12 + length;
  }

  if (depth !== 8) throw new Error(`unsupported bit depth ${depth}; MVP3 handles 8-bit PNGs`);
  if (interlace !== 0) throw new Error("interlaced PNGs are not supported");

  const channels = { 0: 1, 2: 3, 3: 1, 4: 2, 6: 4 }[colorType];
  if (!channels) throw new Error(`unsupported PNG colour type ${colorType}`);

  const samples = unfilter(inflateSync(Buffer.concat(idat)), width, height, channels);
  const data = new Uint8Array(width * height * 4);
  for (let i = 0, n = width * height; i < n; i += 1) {
    const s = i * channels;
    const d = i * 4;
    if (colorType === 3) {
      const index = samples[s];
      data[d] = palette[index * 3];
      data[d + 1] = palette[index * 3 + 1];
      data[d + 2] = palette[index * 3 + 2];
      data[d + 3] = paletteAlpha && index < paletteAlpha.length ? paletteAlpha[index] : 255;
    } else if (colorType === 6) {
      data[d] = samples[s];
      data[d + 1] = samples[s + 1];
      data[d + 2] = samples[s + 2];
      data[d + 3] = samples[s + 3];
    } else if (colorType === 2) {
      data[d] = samples[s];
      data[d + 1] = samples[s + 1];
      data[d + 2] = samples[s + 2];
      data[d + 3] = 255;
    } else if (colorType === 0) {
      data[d] = data[d + 1] = data[d + 2] = samples[s];
      data[d + 3] = 255;
    } else {
      data[d] = data[d + 1] = data[d + 2] = samples[s];
      data[d + 3] = samples[s + 1];
    }
  }
  return { width, height, data, sourceColorType: colorType };
}

function chunk(type, body) {
  const head = Buffer.alloc(8);
  head.writeUInt32BE(body.length, 0);
  head.write(type, 4, "latin1");
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(Buffer.concat([head.subarray(4), body])), 0);
  return Buffer.concat([head, body, crc]);
}

function encode(width, height, channels, colorType, samples) {
  const stride = width * channels;
  const raw = Buffer.alloc((stride + 1) * height);
  for (let y = 0; y < height; y += 1) {
    raw[y * (stride + 1)] = 0; // filter: None keeps the writer trivial and lossless
    Buffer.from(samples.buffer ?? samples, samples.byteOffset ?? 0, samples.length)
      .copy(raw, y * (stride + 1) + 1, y * stride, (y + 1) * stride);
  }
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8;
  ihdr[9] = colorType;
  return Buffer.concat([
    SIGNATURE,
    chunk("IHDR", ihdr),
    chunk("IDAT", deflateSync(raw, { level: 9 })),
    chunk("IEND", Buffer.alloc(0)),
  ]);
}

/** Encode straight RGBA samples (4 bytes per pixel) as an 8-bit RGBA PNG. */
export function encodeRgbaPng(width, height, rgba) {
  return encode(width, height, 4, 6, rgba);
}

/** Encode single-channel samples as an 8-bit greyscale PNG. */
export function encodeGrayPng(width, height, gray) {
  return encode(width, height, 1, 0, gray);
}
