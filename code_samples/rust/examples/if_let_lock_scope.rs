//! The edition 2024 `if let` temporary scope, shown with the same source in two editions.
//! Run: cargo run --example if_let_lock_scope
//! To see the 2021 behaviour: rustc --edition 2021 examples/if_let_lock_scope.rs -o /tmp/x && /tmp/x
use std::sync::Mutex;

fn main() {
    let m = Mutex::new(Some(1));
    // `None` never matches here, so the `else` branch runs.
    if let None = *m.lock().unwrap() {
        println!("unreachable");
    } else {
        // 2021: the guard from the scrutinee is still alive here -> try_lock fails
        // 2024: the guard is dropped before `else` -> try_lock succeeds
        println!("else branch, try_lock ok = {}", m.try_lock().is_ok());
    }
    println!("done");
}
