use std::future::Future;
use std::sync::Mutex;

async fn yield_now() {}

async fn holds_guard(m: &Mutex<u32>) {
    let guard = m.lock().unwrap();
    yield_now().await;
    println!("{}", *guard);
}

fn require_send<F: Future + Send>(_f: F) {}

fn main() {
    let m = Mutex::new(1);
    require_send(holds_guard(&m));
}
