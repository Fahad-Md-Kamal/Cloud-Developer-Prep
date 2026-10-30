//! Compiles fine but FAILS AT RUN TIME on wasm32-unknown-unknown (std has no clock or threads there).
//!     rustc --edition 2024 --target wasm32-unknown-unknown --crate-type=cdylib -C panic=abort limits/limits_run.rs
#[unsafe(no_mangle)]
pub extern "C" fn spawn_ok() -> i32 {
    std::thread::Builder::new().spawn(|| {}).is_ok() as i32
}

#[unsafe(no_mangle)]
pub extern "C" fn clock() -> i32 {
    std::time::Instant::now().elapsed().as_nanos() as i32
}
