#!/bin/sh
# Compile each file in demo_app/compile_fail/ against the proc-macro crate and show the errors.
set -eu
cd "$(dirname "$0")"
cargo build -p demo_macros
TARGET_DIR="${CARGO_TARGET_DIR:-target}/debug"
LIB=$(ls "$TARGET_DIR"/libdemo_macros.* | grep -E '\.(so|dylib|dll)$' | head -1)
for f in demo_app/compile_fail/*.rs; do
  echo "== $f"
  rustc --edition 2024 --emit=metadata -o /tmp/out_macros --extern demo_macros="$LIB" -L "$TARGET_DIR/deps" "$f" 2>&1 || true
done
