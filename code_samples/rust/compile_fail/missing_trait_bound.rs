fn largest<T>(items: &[T]) -> &T {
    let mut m = &items[0];
    for i in items {
        if i > m {
            m = i;
        }
    }
    m
}

fn main() {
    println!("{}", largest(&[1, 2, 3]));
}
