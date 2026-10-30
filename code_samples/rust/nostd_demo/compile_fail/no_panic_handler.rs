//! Must FAIL: a no_std binary needs a panic handler.
//!     rustc --edition 2024 --target thumbv7em-none-eabihf -C panic=abort --crate-type=bin compile_fail/no_panic_handler.rs
#![no_std]
#![no_main]

#[unsafe(no_mangle)]
pub extern "C" fn main() -> ! {
    loop {}
}
