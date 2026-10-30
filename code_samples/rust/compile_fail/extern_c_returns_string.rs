// `extern "C"` needs FFI-safe types; `String` and `Vec` have no stable C layout (lint `improper_ctypes_definitions` warns).
#[unsafe(no_mangle)]
pub extern "C" fn name() -> String {
    String::from("hi")
}

fn main() {}
