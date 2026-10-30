use std::future::Future;
use std::rc::Rc;

async fn yield_now() {}

async fn uses_rc() {
    let local = Rc::new(1);
    yield_now().await;
    println!("{local}");
}

fn require_send<F: Future + Send>(_f: F) {}

fn main() {
    require_send(uses_rc());
}
