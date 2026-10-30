// transmute checks sizes at compile time, but nothing else.
fn main() {
    let a: u32 = 1;
    let b: u64 = unsafe { std::mem::transmute(a) };
    println!("{b}");
}
