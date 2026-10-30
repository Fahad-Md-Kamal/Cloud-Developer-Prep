use std::thread;

fn main() {
    let mut counter = 0;
    let a = thread::spawn(|| counter += 1);
    let b = thread::spawn(|| counter += 1);
    a.join().unwrap();
    b.join().unwrap();
    println!("{counter}");
}
