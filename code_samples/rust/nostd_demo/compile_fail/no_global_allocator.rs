//! Must FAIL: `alloc` needs a #[global_allocator] in a binary.
//!     rustc --edition 2024 --target thumbv7em-none-eabihf -C panic=abort --crate-type=staticlib compile_fail/no_global_allocator.rs
#![no_std]
extern crate alloc;

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}

#[unsafe(no_mangle)]
pub extern "C" fn make() -> usize {
    alloc::vec![1u8, 2, 3].len()
}
