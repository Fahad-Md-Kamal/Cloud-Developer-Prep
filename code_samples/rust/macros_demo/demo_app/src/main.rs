//! Uses the three proc macros. Run: cargo run -p demo_app   (from code_samples/rust/macros_demo)

use demo_macros::{Describe, passthrough, shout, timed};

// Attribute macro on an out-of-line module: stable since Rust 1.99.
#[passthrough]
mod inner;

#[allow(dead_code)]
#[derive(Describe)]
struct User {
    id: u64,
    name: String,
    tags: Vec<String>,
}

#[allow(dead_code)]
#[derive(Describe)]
struct Wrapper<T> {
    inner: T,
}

#[timed]
fn slow_sum(n: u64) -> u64 {
    (1..=n).sum()
}

fn main() {
    println!("{}", User::describe());
    println!("{}", Wrapper::<u8>::describe());
    println!("slow_sum(1000) = {}", slow_sum(1000));
    println!("{}", shout!("quiet text"));
    println!("{}", inner::hello());
}
