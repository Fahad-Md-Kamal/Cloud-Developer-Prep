//! Must FAIL to link on wasm since 1.96: an `extern` function nobody defines.
//!     rustc --edition 2024 --target wasm32-unknown-unknown --crate-type=cdylib compile_fail/undefined_import.rs
unsafe extern "C" {
    fn host_log(x: i32);
}

#[unsafe(no_mangle)]
pub extern "C" fn run() {
    unsafe { host_log(1) }
}
