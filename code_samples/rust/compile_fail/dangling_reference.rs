fn make<'a>() -> &'a String {
    let s = String::from("temp");
    &s
}

fn main() {
    println!("{}", make());
}
