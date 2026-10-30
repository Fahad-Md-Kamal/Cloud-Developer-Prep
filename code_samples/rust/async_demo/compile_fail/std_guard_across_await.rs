use std::sync::{Arc, Mutex};
use std::time::Duration;

#[tokio::main]
async fn main() {
    let data = Arc::new(Mutex::new(0));
    let d = Arc::clone(&data);
    let handle = tokio::spawn(async move {
        let mut guard = d.lock().unwrap();
        *guard += 1;
        tokio::time::sleep(Duration::from_millis(1)).await;
    });
    handle.await.unwrap();
}
