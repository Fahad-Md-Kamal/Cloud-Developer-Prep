#!/bin/sh
# Compile each file in compile_fail/ as an example; every one must FAIL.
# Usage: ./run_compile_fail.sh [name]   (prints the real compiler error)
cd "$(dirname "$0")" || exit 1
for f in ${1:-std_guard_across_await spawn_borrows_local}; do
  echo "=== $f"
  cp "compile_fail/$f.rs" "examples/zz_$f.rs"
  cargo build -q --example "zz_$f" 2>&1 | head -40
  rm -f "examples/zz_$f.rs"
done
