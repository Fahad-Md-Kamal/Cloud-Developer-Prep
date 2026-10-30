//! Why you must not block the executor. Run: cargo run --example blocking_the_executor
use std::time::{Duration, Instant};
use tokio::time::sleep;

/// Spawn a 50 ms timer, let it start, run `work`, then report how late the timer fired.
async fn measure(label: &str, work: impl AsyncFnOnce()) {
    let timer = tokio::spawn(async {
        let start = Instant::now();
        sleep(Duration::from_millis(50)).await;
        start.elapsed()
    });
    tokio::task::yield_now().await; // let the timer task start
    work().await;
    let elapsed = timer.await.unwrap();
    println!("   {label}: the 50 ms timer fired after {} ms", elapsed.as_millis() / 10 * 10);
}

#[tokio::main(flavor = "current_thread")]
async fn main() {
    println!("single-threaded runtime:");
    measure("std::thread::sleep(300ms) in the task", async || {
        std::thread::sleep(Duration::from_millis(300));
    })
    .await;
    measure("spawn_blocking(sleep 300ms)         ", async || {
        tokio::task::spawn_blocking(|| std::thread::sleep(Duration::from_millis(300)))
            .await
            .unwrap();
    })
    .await;
}
