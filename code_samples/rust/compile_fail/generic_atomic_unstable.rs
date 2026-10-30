use std::sync::atomic::{Atomic, Ordering};

fn main() {
    let g: Atomic<u32> = Atomic::new(7);
    println!("{}", g.load(Ordering::Relaxed));
}
