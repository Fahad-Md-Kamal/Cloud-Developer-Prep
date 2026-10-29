use std::thread;

fn main() {
    let data = vec![1, 2, 3];
    let handle = thread::spawn(|| {
        println!("{data:?}");
    });
    handle.join().unwrap();
}
