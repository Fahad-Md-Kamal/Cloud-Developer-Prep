// Loads the compiled module in Node and calls it.
import { readFileSync } from "node:fs";
const url = new URL("./target/wasm32-unknown-unknown/release/wasm_demo.wasm", import.meta.url);
const path = process.env.WASM_PATH ?? url.pathname;
const { instance } = await WebAssembly.instantiate(readFileSync(path), {});
const w = instance.exports;
console.log("add(2, 40) =", w.add(2, 40));
console.log("fib(50)    =", w.fib(50)); // returns a BigInt: u64 maps to i64
const bytes = new TextEncoder().encode("hello wasm");
const ptr = w.alloc(bytes.length);
new Uint8Array(w.memory.buffer, ptr, bytes.length).set(bytes);
console.log("checksum   =", w.checksum(ptr, bytes.length) >>> 0); // >>> 0: JS sees u32 as i32
console.log("exports    =", Object.keys(w).join(", "));
