// `Cell<&'a T>` is invariant in 'a: you cannot shorten it, because someone could write a short borrow into it.
use std::cell::Cell;

fn main() {
    let long: Cell<&'static str> = Cell::new("long");
    let short: &Cell<&str> = &long;
    let local = String::from("short");
    short.set(&local);
    println!("{}", long.get());
}
