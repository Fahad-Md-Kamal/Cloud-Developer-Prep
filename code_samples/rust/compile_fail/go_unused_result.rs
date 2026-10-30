// Go lets you drop an `err` silently. Rust warns when a Result is ignored.
#![deny(unused_must_use)]
fn parse(s: &str) -> Result<i32, std::num::ParseIntError> {
    s.parse()
}
fn main() {
    parse("1");
}
