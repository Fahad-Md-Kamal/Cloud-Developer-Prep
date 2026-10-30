const m = require("./pkg/wasm_bindgen_demo.js");
console.log(m.greet("Rust"));
const c = new m.Counter();
c.bump(); console.log("counter =", c.bump());
c.free(); // JS owns the wasm-side struct: free it (or use `using`)
m.each(new Uint32Array([1, 2, 3]), { call: (x) => console.log("callback", x) });
