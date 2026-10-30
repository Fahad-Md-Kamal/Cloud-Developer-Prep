//! A normal `std` program compiled to WASI (WebAssembly System Interface).
//!     rustup target add wasm32-wasip1
//!     cargo build --release --target wasm32-wasip1 --example hello_wasi
//!     node run_wasi.mjs
use std::{env, fs};

fn main() {
    println!("args: {:?}", env::args().collect::<Vec<_>>());
    println!("HOME-like var: {:?}", env::var("DEMO"));
    fs::write("/sandbox/out.txt", "written from wasm").unwrap();
    println!("read back: {}", fs::read_to_string("/sandbox/out.txt").unwrap());
}
