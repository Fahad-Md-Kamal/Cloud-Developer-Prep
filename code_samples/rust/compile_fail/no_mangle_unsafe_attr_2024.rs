// Edition 2024: `no_mangle` is an unsafe attribute and must be written `#[unsafe(no_mangle)]`.
#[no_mangle]
pub extern "C" fn exported() -> i32 {
    1
}

fn main() {}
