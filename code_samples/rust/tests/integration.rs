//! Integration tests: compiled as a separate crate, so they can only use the PUBLIC API.

use guru_samples::{Stack, parse_duration, slugify};

#[test]
fn public_api_works_together() {
    let title = "Rust: Ownership & Borrowing";
    assert_eq!(slugify(title), "rust-ownership-borrowing");
    assert_eq!(parse_duration("90s").unwrap().as_secs(), 90);
}

#[test]
fn stack_is_lifo() {
    let mut s = Stack::new();
    s.push(1);
    s.push(2);
    assert_eq!(s.pop_or_panic(), 2);
    assert_eq!(s.len(), 1);
    assert!(!s.is_empty());
}
