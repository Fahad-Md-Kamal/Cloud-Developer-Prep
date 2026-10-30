//! wasm-bindgen: strings, structs and JS callbacks across the boundary.
//!     cargo build --release --target wasm32-unknown-unknown
//!     wasm-bindgen --target nodejs --out-dir pkg target/wasm32-unknown-unknown/release/wasm_bindgen_demo.wasm
//!     node run.cjs   (the CLI version must match the crate version in Cargo.lock)
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
extern "C" {
    #[wasm_bindgen(js_namespace = console)]
    fn log(s: &str);
}

#[wasm_bindgen]
pub fn greet(name: &str) -> String {
    log(&format!("Rust sees name = {name}"));
    format!("Hello, {name}!")
}

#[wasm_bindgen]
pub struct Counter {
    n: u32,
}

#[wasm_bindgen]
impl Counter {
    #[wasm_bindgen(constructor)]
    pub fn new() -> Counter {
        Counter { n: 0 }
    }

    pub fn bump(&mut self) -> u32 {
        self.n += 1;
        self.n
    }
}

impl Default for Counter {
    fn default() -> Self {
        Self::new()
    }
}

/// Calls back into JS for every item.
#[wasm_bindgen]
pub fn each(items: Vec<u32>, f: &js_sys_free::Callback) {
    for i in items {
        f.call(i);
    }
}

mod js_sys_free {
    use wasm_bindgen::prelude::*;
    #[wasm_bindgen]
    extern "C" {
        pub type Callback;
        #[wasm_bindgen(method, js_name = call)]
        pub fn call(this: &Callback, x: u32);
    }
}
