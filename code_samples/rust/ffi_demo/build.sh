#!/bin/sh
# Build the Rust library, compile demo.c against it (static and dynamic), and run both.
set -eu
cd "$(dirname "$0")"
cargo build --release --lib
TARGET_DIR="${CARGO_TARGET_DIR:-target}/release"
echo "== static link"
cc demo.c "$TARGET_DIR/libffi_demo.a" -o "$TARGET_DIR/demo_static"
"$TARGET_DIR/demo_static"
echo "== dynamic link"
cc demo.c -L"$TARGET_DIR" -lffi_demo -o "$TARGET_DIR/demo_dynamic"
case "$(uname)" in
  Darwin) DYLD_LIBRARY_PATH="$TARGET_DIR" "$TARGET_DIR/demo_dynamic" ;;
  *)      LD_LIBRARY_PATH="$TARGET_DIR" "$TARGET_DIR/demo_dynamic" ;;
esac
