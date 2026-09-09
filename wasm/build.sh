#!/usr/bin/env bash
# Rebuild wasm/ladder.wasm (Rust wasm32 + SIMD). Committed binary is what Pages serves.
set -euo pipefail
cd "$(dirname "$0")"
rustc --target wasm32-unknown-unknown \
  -O -C lto -C panic=abort -C target-feature=+simd128 \
  --crate-type cdylib \
  ladder.rs -o ladder.wasm
ls -l ladder.wasm
