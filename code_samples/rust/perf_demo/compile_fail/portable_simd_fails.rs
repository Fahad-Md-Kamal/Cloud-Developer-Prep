//! This file must FAIL on stable: std::simd is still unstable.
//!     rustc --edition 2024 --emit=metadata -o /tmp/out compile_fail/portable_simd_fails.rs
use std::simd::f32x4;

fn main() {
    let a = f32x4::splat(1.0);
    println!("{a:?}");
}
