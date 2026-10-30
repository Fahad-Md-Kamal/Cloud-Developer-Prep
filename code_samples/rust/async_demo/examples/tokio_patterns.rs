//! Tokio patterns. Run: cargo run --example tokio_patterns
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::{broadcast, mpsc, oneshot, watch, Mutex, Semaphore};
use tokio::task::JoinSet;
use tokio::time::{sleep, timeout};
use tokio_stream::{wrappers::ReceiverStream, StreamExt};
use tokio_util::sync::CancellationToken;

// ---- actor: one task owns the state, others send messages ----
enum Msg {
    Add(u64),
    Get(oneshot::Sender<u64>),
}

fn spawn_counter_actor() -> mpsc::Sender<Msg> {
    let (tx, mut rx) = mpsc::channel(16);
    tokio::spawn(async move {
        let mut total = 0;
        while let Some(m) = rx.recv().await {
            match m {
                Msg::Add(n) => total += n,
                Msg::Get(reply) => {
                    let _ = reply.send(total);
                }
            }
        }
    });
    tx
}

#[tokio::main]
async fn main() {
    // 1. spawn, JoinHandle and JoinError (a panic inside a task is caught)
    let ok = tokio::spawn(async { 1 + 1 });
    let bad = tokio::spawn(async {
        if true {
            panic!("task blew up");
        }
        0
    });
    println!("1. ok = {:?}", ok.await);
    let err = bad.await.unwrap_err();
    println!("   bad: is_panic = {}", err.is_panic());

    // 2. JoinSet: structured fan-out, results as they finish
    let mut set = JoinSet::new();
    for i in 1..=3u64 {
        set.spawn(async move {
            sleep(Duration::from_millis(30 * (4 - i))).await;
            i
        });
    }
    let mut order = vec![];
    while let Some(r) = set.join_next().await {
        order.push(r.unwrap());
    }
    println!("2. JoinSet finish order: {order:?}");

    // 3. timeout and select! (the loser future is DROPPED, i.e. cancelled)
    let r = timeout(Duration::from_millis(20), sleep(Duration::from_secs(5))).await;
    println!("3. timeout elapsed: {}", r.is_err());
    tokio::select! {
        _ = sleep(Duration::from_millis(10)) => println!("   select: timer won"),
        _ = sleep(Duration::from_secs(5)) => println!("   select: slow won"),
    }

    // 4. channels
    let (tx, rx) = oneshot::channel();
    tokio::spawn(async move { tx.send("reply").unwrap() });
    println!("4. oneshot: {}", rx.await.unwrap());

    let (btx, mut b1) = broadcast::channel(8);
    let mut b2 = btx.subscribe();
    btx.send("hello all").unwrap();
    println!("   broadcast: {} / {}", b1.recv().await.unwrap(), b2.recv().await.unwrap());

    let (wtx, mut wrx) = watch::channel(0);
    wtx.send(1).unwrap();
    wtx.send(2).unwrap();
    wrx.changed().await.unwrap();
    println!("   watch keeps only the latest: {}", *wrx.borrow());

    // 5. backpressure: a bounded channel makes the producer wait
    let (tx, mut rx) = mpsc::channel::<u32>(2);
    let producer = tokio::spawn(async move {
        let t = Instant::now();
        for i in 0..5 {
            tx.send(i).await.unwrap(); // waits when 2 items are queued
        }
        t.elapsed()
    });
    sleep(Duration::from_millis(100)).await; // slow consumer
    let mut got = vec![];
    while let Some(v) = rx.recv().await {
        got.push(v);
    }
    println!("5. bounded channel delivered {got:?}; producer was held back {}",
        producer.await.unwrap() >= Duration::from_millis(90));

    // 6. Semaphore limits concurrency
    let sem = Arc::new(Semaphore::new(2));
    let running = Arc::new(std::sync::atomic::AtomicUsize::new(0));
    let peak = Arc::new(std::sync::atomic::AtomicUsize::new(0));
    let mut set = JoinSet::new();
    for _ in 0..6 {
        let (sem, running, peak) = (sem.clone(), running.clone(), peak.clone());
        set.spawn(async move {
            let _permit = sem.acquire_owned().await.unwrap();
            let now = running.fetch_add(1, std::sync::atomic::Ordering::SeqCst) + 1;
            peak.fetch_max(now, std::sync::atomic::Ordering::SeqCst);
            sleep(Duration::from_millis(20)).await;
            running.fetch_sub(1, std::sync::atomic::Ordering::SeqCst);
        });
    }
    while set.join_next().await.is_some() {}
    println!("6. peak concurrency with Semaphore(2): {}", peak.load(std::sync::atomic::Ordering::SeqCst));

    // 7. graceful shutdown with CancellationToken
    let token = CancellationToken::new();
    let worker_token = token.clone();
    let worker = tokio::spawn(async move {
        let mut ticks = 0;
        loop {
            tokio::select! {
                _ = worker_token.cancelled() => {
                    // finish current work / flush, then leave
                    return ticks;
                }
                _ = sleep(Duration::from_millis(10)) => ticks += 1,
            }
        }
    });
    sleep(Duration::from_millis(55)).await;
    token.cancel();
    let ticks = worker.await.unwrap();
    println!("7. worker stopped cleanly after {ticks} ticks (timing dependent, about 4 to 5)");
    assert!(ticks >= 3);

    // 8. spawn_blocking for CPU/blocking work
    let sum = tokio::task::spawn_blocking(|| (1..=1_000_000u64).sum::<u64>()).await.unwrap();
    println!("8. spawn_blocking result: {sum}");

    // 9. actor
    let actor = spawn_counter_actor();
    for n in 1..=4 {
        actor.send(Msg::Add(n)).await.unwrap();
    }
    let (rtx, rrx) = oneshot::channel();
    actor.send(Msg::Get(rtx)).await.unwrap();
    println!("9. actor total: {}", rrx.await.unwrap());

    // 10. async Mutex lets you hold the guard across .await
    let shared = Arc::new(Mutex::new(0));
    let g = shared.lock().await;
    sleep(Duration::from_millis(5)).await; // fine with tokio::sync::Mutex
    drop(g);
    println!("10. tokio Mutex guard held across await: ok");

    // 11. streams
    let (tx, rx) = mpsc::channel(4);
    tokio::spawn(async move {
        for i in 0..5 {
            tx.send(i).await.unwrap();
        }
    });
    let evens: Vec<_> = ReceiverStream::new(rx).filter(|n| n % 2 == 0).map(|n| n * 10).collect().await;
    println!("11. stream filter/map: {evens:?}");
}
