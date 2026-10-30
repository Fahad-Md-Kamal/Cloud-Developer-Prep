// A macro call that matches no rule is a compile error.
macro_rules! pair {
    ($a:expr, $b:expr) => {
        ($a, $b)
    };
}

fn main() {
    let p = pair!(1);
    println!("{:?}", p);
}
