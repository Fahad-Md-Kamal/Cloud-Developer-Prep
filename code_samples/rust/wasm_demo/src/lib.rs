//! Plain WebAssembly without wasm-bindgen: only numbers cross the boundary.
//!     rustup target add wasm32-unknown-unknown
//!     cargo build --release --target wasm32-unknown-unknown
//!     node run.mjs

#[unsafe(no_mangle)]
pub extern "C" fn add(a: i32, b: i32) -> i32 {
    a + b
}

#[unsafe(no_mangle)]
pub extern "C" fn fib(n: u32) -> u64 {
    let (mut a, mut b) = (0u64, 1u64);
    for _ in 0..n {
        (a, b) = (b, a + b);
    }
    a
}

/// Hands JS a pointer into wasm linear memory; JS writes bytes there, then calls `checksum`.
#[unsafe(no_mangle)]
pub extern "C" fn alloc(len: usize) -> *mut u8 {
    let mut v = Vec::<u8>::with_capacity(len);
    let p = v.as_mut_ptr();
    core::mem::forget(v);
    p
}

/// # Safety
/// `ptr` and `len` must come from `alloc` (same length).
#[unsafe(no_mangle)]
pub unsafe extern "C" fn checksum(ptr: *mut u8, len: usize) -> u32 {
    // Taking ownership back means the buffer is freed when `v` drops.
    let v = unsafe { Vec::from_raw_parts(ptr, len, len) };
    v.iter().fold(0u32, |h, &b| h.wrapping_mul(31).wrapping_add(b as u32))
}
