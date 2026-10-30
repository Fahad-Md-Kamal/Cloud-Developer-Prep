//! Compiler hints and SIMD on stable. Run: cargo run --release --example hints_and_simd
use std::hint::{cold_path, select_unpredictable};

fn parse(s: &str) -> u32 {
    match s.parse::<u32>() {
        Ok(n) => n,
        Err(_) => {
            cold_path(); // tell the optimizer the error path is rare
            0
        }
    }
}

fn clamp_branchless(x: i32, lo: i32, hi: i32) -> i32 {
    let x = select_unpredictable(x < lo, lo, x);
    select_unpredictable(x > hi, hi, x)
}

/// Bounds checks: one assert up front lets the optimizer drop the per-index checks.
fn dot(a: &[f32], b: &[f32]) -> f32 {
    assert_eq!(a.len(), b.len());
    let mut s = 0.0;
    for i in 0..a.len() {
        s += a[i] * b[i];
    }
    s
}

#[cfg(target_arch = "aarch64")]
fn add4_neon(a: [f32; 4], b: [f32; 4]) -> [f32; 4] {
    use std::arch::aarch64::*;
    // NEON is part of the aarch64 baseline, so this is safe to call (the intrinsics are unsafe fns).
    unsafe {
        let r = vaddq_f32(vld1q_f32(a.as_ptr()), vld1q_f32(b.as_ptr()));
        let mut out = [0.0; 4];
        vst1q_f32(out.as_mut_ptr(), r);
        out
    }
}

fn main() {
    println!("parse: {} {}", parse("42"), parse("x"));
    println!("clamp: {} {} {}", clamp_branchless(-5, 0, 10), clamp_branchless(5, 0, 10), clamp_branchless(50, 0, 10));
    println!("dot: {}", dot(&[1., 2., 3.], &[4., 5., 6.]));
    #[cfg(target_arch = "aarch64")]
    println!("neon add: {:?}", add4_neon([1., 2., 3., 4.], [10., 20., 30., 40.]));
    #[cfg(target_arch = "x86_64")]
    println!("avx2 detected at run time: {}", is_x86_feature_detected!("avx2"));
}
