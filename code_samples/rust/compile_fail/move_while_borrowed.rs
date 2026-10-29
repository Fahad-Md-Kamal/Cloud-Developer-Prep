fn main() {
    let s = String::from("hi");
    let r = &s;
    let moved = s;
    println!("{r} {moved}");
}
