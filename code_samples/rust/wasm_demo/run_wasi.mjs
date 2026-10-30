// Runs the WASI build with Node's built-in `node:wasi` (a preopened directory is the only file access).
import { readFileSync, mkdtempSync, readFileSync as rf } from "node:fs";
import { WASI } from "node:wasi";
import { tmpdir } from "node:os";
import { join } from "node:path";
const dir = mkdtempSync(join(tmpdir(), "wasi-"));
const wasi = new WASI({ version: "preview1", args: ["hello_wasi", "x"], env: { DEMO: "1" }, preopens: { "/sandbox": dir } });
const path = process.env.WASM_PATH ?? new URL("./target/wasm32-wasip1/release/examples/hello_wasi.wasm", import.meta.url).pathname;
const { instance } = await WebAssembly.instantiate(readFileSync(path), wasi.getImportObject());
wasi.start(instance);
console.log("host sees:", rf(join(dir, "out.txt"), "utf8"));
