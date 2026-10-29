// `&mut T` is INVARIANT in T, so a `&mut &'static str` cannot be treated as `&mut &'a str`.
fn assign<'a>(target: &mut &'a str, value: &'a str) {
    *target = value;
}

fn main() {
    let mut hello: &'static str = "hello";
    {
        let world = String::from("world");
        assign(&mut hello, &world);
    }
    println!("{hello}");
}
