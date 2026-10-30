// Edition 2024: an `extern` block must be written `unsafe extern`.
extern "C" {
    fn abs(x: i32) -> i32;
}

fn main() {
    println!("{}", unsafe { abs(-1) });
}
