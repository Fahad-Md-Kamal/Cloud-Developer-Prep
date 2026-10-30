// Python: `b = a` makes two names for one list. Rust: `let b = a` MOVES it.
fn main() {
    let a = vec![1, 2, 3];
    let b = a;
    b.len();
    println!("{:?}", a);
}
