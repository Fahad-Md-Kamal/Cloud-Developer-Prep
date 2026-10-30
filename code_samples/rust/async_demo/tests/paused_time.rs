use std::time::Duration;
use tokio::time::{Instant, sleep, timeout};

/// `start_paused` makes the clock jump forward whenever every task is idle,
/// so a test of a one-hour timeout takes microseconds of real time.
#[tokio::test(start_paused = true)]
async fn hour_long_sleep_is_instant() {
    let real = std::time::Instant::now();
    let start = Instant::now();
    sleep(Duration::from_secs(3600)).await;
    assert!(start.elapsed() >= Duration::from_secs(3600));
    assert!(real.elapsed() < Duration::from_secs(1));
}

#[tokio::test(start_paused = true)]
async fn timeout_fires_deterministically() {
    let r = timeout(Duration::from_secs(5), sleep(Duration::from_secs(60))).await;
    assert!(r.is_err());
}
