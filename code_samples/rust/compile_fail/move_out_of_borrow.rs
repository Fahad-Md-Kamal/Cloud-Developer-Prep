fn main() {
    let names = vec![String::from("a"), String::from("b")];
    let r = &names;
    let first = r[0];
    println!("{first}");
}
