// A struct is invariant in a lifetime if any field makes it so. `Cell<&'a str>` is invariant,
// so `InvStruct<'static>` cannot be passed where `InvStruct<'short>` is expected.
use std::cell::Cell;

#[allow(dead_code)]
struct InvStruct<'a>(Cell<&'a str>);

fn takes<'a>(_a: InvStruct<'a>, _b: &'a str) {}

fn main() {
    let s: InvStruct<'static> = InvStruct(Cell::new("static"));
    let local = String::from("short");
    takes(s, &local);
}
