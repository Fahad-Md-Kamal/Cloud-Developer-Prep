//! A tiny function to read its MIR.
//!     rustc --edition 2024 --crate-type=lib --emit=mir -C opt-level=0 -o - mir_small.rs
pub fn pick(v: &Vec<i32>, i: usize) -> i32 {
    if i < v.len() { v[i] + 1 } else { -1 }
}

macro_rules! twice { ($e:expr) => { $e + $e }; }
pub fn m(x: i32) -> i32 { twice!(x * 2) }
