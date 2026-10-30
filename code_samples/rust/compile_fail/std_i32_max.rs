// The legacy `std::i32::MAX` module constants are deprecated (fully, in 1.99).
// Compile with: rustc --edition 2024 --emit=metadata -o /tmp/out compile_fail/std_i32_max.rs
#![deny(deprecated)]
fn main() {
    println!("{}", std::i32::MAX);
}
