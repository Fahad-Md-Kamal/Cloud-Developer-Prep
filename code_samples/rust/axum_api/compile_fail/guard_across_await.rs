//! Must FAIL to compile: a std MutexGuard held across `.await` makes the future !Send.
use std::sync::{Arc, Mutex};
use axum::{Router, extract::State, routing::get};

async fn handler(State(s): State<Arc<Mutex<u32>>>) -> String {
    let guard = s.lock().unwrap();
    tokio::task::yield_now().await;
    guard.to_string()
}

fn main() {
    let _app: Router = Router::new().route("/", get(handler)).with_state(Arc::new(Mutex::new(0)));
}
