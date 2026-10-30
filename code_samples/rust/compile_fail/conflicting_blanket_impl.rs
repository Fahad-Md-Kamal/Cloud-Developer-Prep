// Coherence: two impls that could apply to the same type are rejected.
use std::fmt::Display;

trait Describe {
    fn describe(&self) -> String;
}

impl<T: Display> Describe for T {
    fn describe(&self) -> String {
        format!("value {self}")
    }
}

impl Describe for i32 {
    fn describe(&self) -> String {
        "an integer".to_string()
    }
}

fn main() {
    println!("{}", 1.describe());
}
