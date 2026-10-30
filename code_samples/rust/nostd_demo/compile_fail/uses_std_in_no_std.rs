//! Must FAIL: `Vec` and `println!` do not exist in `core`.
//!     rustc --edition 2024 --crate-type=lib --emit=metadata -o /tmp/out compile_fail/uses_std_in_no_std.rs
#![no_std]
pub fn f() { let v = Vec::<u8>::new(); println!("{:?}", v); }
