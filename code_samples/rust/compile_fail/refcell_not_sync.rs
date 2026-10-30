use std::cell::RefCell;
use std::thread;

fn main() {
    let cell = RefCell::new(0);
    thread::scope(|s| {
        s.spawn(|| *cell.borrow_mut() += 1);
        s.spawn(|| *cell.borrow_mut() += 1);
    });
}
