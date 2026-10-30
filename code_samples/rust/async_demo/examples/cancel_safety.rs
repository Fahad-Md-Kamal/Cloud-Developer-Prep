//! Cancellation safety with select!. Run: cargo run --example cancel_safety
use std::time::Duration;
use tokio::sync::mpsc;
use tokio::time::sleep;

/// NOT cancellation safe: if dropped after the first recv, `first` is lost.
async fn recv_pair(rx: &mut mpsc::Receiver<u32>) -> Option<(u32, u32)> {
    let first = rx.recv().await?;
    let second = rx.recv().await?; // <- cancellation can happen here
    Some((first, second))
}

#[tokio::main]
async fn main() {
    let (tx, mut rx) = mpsc::channel(8);
    tx.send(1).await.unwrap();

    // The timer fires while recv_pair is waiting for its second item.
    tokio::select! {
        r = recv_pair(&mut rx) => println!("pair: {r:?}"),
        _ = sleep(Duration::from_millis(20)) => println!("timeout, recv_pair future dropped"),
    }
    tx.send(2).await.unwrap();
    tx.send(3).await.unwrap();
    drop(tx);
    let mut rest = vec![];
    while let Some(v) = rx.recv().await {
        rest.push(v);
    }
    println!("items still in the channel: {rest:?}  (the 1 is gone: it was held inside the dropped future)");

    // The fix: keep partial state OUTSIDE the future, so dropping it loses nothing.
    let (tx, mut rx) = mpsc::channel(8);
    tx.send(1).await.unwrap();
    let mut first: Option<u32> = None;
    loop {
        tokio::select! {
            v = rx.recv() => {
                match (first, v) {
                    (None, Some(v)) => first = Some(v),
                    (Some(a), Some(b)) => { println!("fixed pair: ({a}, {b})"); break; }
                    _ => break,
                }
            }
            _ = sleep(Duration::from_millis(20)) => {
                println!("timeout tick, partial state kept: {first:?}");
                tx.send(2).await.unwrap();
            }
        }
    }
}
