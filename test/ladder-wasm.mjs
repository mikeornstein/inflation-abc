#!/usr/bin/env node
"use strict";
/** Node check: WASM SIMD SoA lerp matches scalar reference (ORN-49). */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const wasmPath = path.join(__dirname, "..", "wasm", "ladder.wasm");
const buf = fs.readFileSync(wasmPath);

function assert(cond, msg) {
  if (!cond) { console.error("FAIL:", msg); process.exit(1); }
}

WebAssembly.instantiate(buf).then(({ instance }) => {
  const e = instance.exports;
  assert(e.simd_level() === 128, "simd_level");
  e.reset_heap();
  const n = 5;
  const xyzA = e.alloc(n * 3 * 4);
  const xyzB = e.alloc(n * 3 * 4);
  const x0 = e.alloc(8 * 4), y0 = e.alloc(8 * 4), z0 = e.alloc(8 * 4);
  const x1 = e.alloc(8 * 4), y1 = e.alloc(8 * 4), z1 = e.alloc(8 * 4);
  const out = e.alloc(n * 3 * 4);
  const mem = new Float32Array(e.memory.buffer);
  const fA = new Float32Array(e.memory.buffer, xyzA, n * 3);
  const fB = new Float32Array(e.memory.buffer, xyzB, n * 3);
  const fO = new Float32Array(e.memory.buffer, out, n * 3);
  for (let i = 0; i < n; i++) {
    fA[i * 3] = i; fA[i * 3 + 1] = i + 10; fA[i * 3 + 2] = i + 20;
    fB[i * 3] = i + 100; fB[i * 3 + 1] = i + 200; fB[i * 3 + 2] = i + 300;
  }
  e.pack_soa(n, xyzA, x0, y0, z0);
  e.pack_soa(n, xyzB, x1, y1, z1);

  // exact rung (w1=0)
  e.lerp_soa(n, 1, 0, x0, y0, z0, x1, y1, z1, out);
  for (let i = 0; i < n * 3; i++) {
    assert(Math.abs(fO[i] - fA[i]) < 1e-6, "exact rung " + i + " " + fO[i] + " vs " + fA[i]);
  }

  // midpoint
  e.lerp_soa(n, 0.5, 0.5, x0, y0, z0, x1, y1, z1, out);
  for (let i = 0; i < n * 3; i++) {
    const want = 0.5 * fA[i] + 0.5 * fB[i];
    assert(Math.abs(fO[i] - want) < 1e-5, "mid " + i + " " + fO[i] + " vs " + want);
  }

  const lamA = e.alloc(4), lamB = e.alloc(4), lamO = e.alloc(4);
  const la = new Float32Array(e.memory.buffer, lamA, 1);
  const lb = new Float32Array(e.memory.buffer, lamB, 1);
  const lo = new Float32Array(e.memory.buffer, lamO, 1);
  la[0] = 1.0; lb[0] = 2.0;
  e.lerp_scalar(1, 0.25, 0.75, lamA, lamB, lamO);
  assert(Math.abs(lo[0] - 1.75) < 1e-6, "lam lerp " + lo[0]);

  console.log("ok  wasm SIMD SoA lerp  n=5  simd128");
}).catch((err) => { console.error(err); process.exit(1); });
