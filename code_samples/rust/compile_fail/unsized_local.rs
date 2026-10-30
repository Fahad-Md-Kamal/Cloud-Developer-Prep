// Locals and arguments must have a size known at compile time.
fn show(s: str) {
    let _ = &s;
}

fn main() {
    let v: str = *"hello";
    let _ = v;
}
