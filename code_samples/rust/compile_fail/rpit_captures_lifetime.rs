// Edition 2024: `impl Trait` in return position captures ALL in-scope lifetimes.
fn count_up(_label: &str, n: u32) -> impl Iterator<Item = u32> {
    0..n
}

fn main() {
    let it = {
        let tmp = String::from("temp label");
        count_up(&tmp, 3)
    };
    println!("{:?}", it.collect::<Vec<_>>());
}
