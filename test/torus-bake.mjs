#!/usr/bin/env node
"use strict";
/** Node check: committed torus bake is a closed all-quad shell (ORN-52). */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const meshDir = path.join(__dirname, "..", "meshes");

function assert(cond, msg) {
  if (!cond) { console.error("FAIL:", msg); process.exit(1); }
}

function edgeKey(a, b) { return a < b ? a + "_" + b : b + "_" + a; }

function gates(data) {
  const n = data.pos0.length / 3;
  const quads = data.quads || [];
  const extra = data.faceTris || [];
  const ec = new Map();
  function add(a, b) {
    const k = edgeKey(a, b);
    ec.set(k, (ec.get(k) || 0) + 1);
  }
  for (const q of quads) {
    assert(q.length === 4, "non-quad");
    for (let i = 0; i < 4; i++) add(q[i], q[(i + 1) % 4]);
  }
  for (const t of extra) {
    for (let i = 0; i < 3; i++) add(t[i], t[(i + 1) % 3]);
  }
  let free = 0, nonman = 0;
  for (const c of ec.values()) {
    if (c === 1) free++;
    if (c > 2) nonman++;
  }
  const nF = quads.length + extra.length;
  const euler = n - ec.size + nF;
  return { n, nQuads: quads.length, free, nonman, euler };
}

const demo = path.join(meshDir, "torus-demo.json");
assert(fs.existsSync(demo), "missing meshes/torus-demo.json");
const d = JSON.parse(fs.readFileSync(demo, "utf8"));
const g = gates(d);
assert(g.free === 0, "freeEdges " + g.free);
assert(g.nonman === 0, "nonManifold " + g.nonman);
assert(g.euler === 0, "euler " + g.euler + " (want torus χ=0)");
assert(g.nQuads >= 64, "too few quads");
assert(g.n <= 8000, "N cap");
assert((d.faceTris || []).length === 0, "torus should be all-quad");
assert(d.meta && d.meta.id === "torus", "meta.id");

for (const level of [1, 2, 4, 5]) {
  const p = path.join(meshDir, "torus-demo.d" + level + ".json");
  assert(fs.existsSync(p), "missing " + p);
  const gd = gates(JSON.parse(fs.readFileSync(p, "utf8")));
  assert(gd.free === 0 && gd.euler === 0, "density " + level + " gates " + JSON.stringify(gd));
}

console.log("ok  torus bake  N=" + g.n + " quads=" + g.nQuads + " free=0 euler=0");
