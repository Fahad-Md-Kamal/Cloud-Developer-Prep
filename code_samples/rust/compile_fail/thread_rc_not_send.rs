use std::rc::Rc;
use std::thread;

fn main() {
    let shared = Rc::new(5);
    let s2 = Rc::clone(&shared);
    let h = thread::spawn(move || println!("{s2}"));
    h.join().unwrap();
}
