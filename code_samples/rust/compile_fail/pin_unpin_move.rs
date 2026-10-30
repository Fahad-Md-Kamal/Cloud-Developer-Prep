use std::marker::PhantomPinned;
use std::pin::Pin;

struct SelfRef {
    _pin: PhantomPinned,
    value: u32,
}

fn main() {
    let mut a = SelfRef { _pin: PhantomPinned, value: 1 };
    let mut pinned = Pin::new(&mut a);
    pinned.value = 2;
}
