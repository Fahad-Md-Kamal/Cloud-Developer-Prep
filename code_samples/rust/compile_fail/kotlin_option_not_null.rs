// Kotlin: `val n: Int? = ...; n + 1` is rejected, you must unwrap with ?. or ?:
// Rust is just as strict: an Option<i32> is not an i32.
fn main() {
    let n: Option<i32> = "5".parse().ok();
    let total: i32 = n + 1;
    println!("{total}");
}
