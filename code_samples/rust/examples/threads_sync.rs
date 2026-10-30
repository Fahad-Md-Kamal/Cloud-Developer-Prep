//! Threads and synchronization with std only.
//! Run: cargo run --example threads_sync
use std::cell::RefCell;
use std::sync::mpsc;
use std::sync::{Arc, Barrier, Condvar, Mutex, OnceLock, RwLock};
use std::thread;
use std::time::Duration;

static CONFIG: OnceLock<String> = OnceLock::new();
thread_local! {
    static COUNTER: RefCell<u32> = const { RefCell::new(0) };
}

fn main() {
    // 1. spawn + join, the closure must be 'static, so we move.
    let h = thread::spawn(|| (1..=10).sum::<u32>());
    println!("1. spawn/join: {}", h.join().unwrap());

    // 2. scoped threads borrow local data.
    let mut data = vec![1, 2, 3, 4, 5, 6];
    let (left, right) = data.split_at_mut(3);
    thread::scope(|s| {
        s.spawn(|| left.iter_mut().for_each(|x| *x *= 10));
        s.spawn(|| right.iter_mut().for_each(|x| *x *= 100));
    });
    println!("2. scoped: {data:?}");

    // 3. Arc<Mutex<T>>
    let total = Arc::new(Mutex::new(0u64));
    let hs: Vec<_> = (0..8)
        .map(|_| {
            let total = Arc::clone(&total);
            thread::spawn(move || {
                for _ in 0..1000 {
                    *total.lock().unwrap() += 1;
                }
            })
        })
        .collect();
    hs.into_iter().for_each(|h| h.join().unwrap());
    println!("3. Arc<Mutex>: {}", *total.lock().unwrap());

    // 4. poisoning
    let m = Arc::new(Mutex::new(5));
    let m2 = Arc::clone(&m);
    let r = thread::spawn(move || {
        let _g = m2.lock().unwrap();
        panic!("boom while holding the lock");
    })
    .join();
    println!(
        "4. thread panicked: {}, poisoned: {}",
        r.is_err(),
        m.is_poisoned()
    );
    let v = m.lock().unwrap_or_else(|e| e.into_inner());
    println!("   recovered value: {}", *v);
    drop(v);

    // 5. RwLock with downgrade (stable 1.92)
    let rw = RwLock::new(String::from("v1"));
    let mut w = rw.write().unwrap();
    w.push_str("-edited");
    let r = std::sync::RwLockWriteGuard::downgrade(w);
    println!("5. downgraded to read guard: {}", *r);
    drop(r);

    // 6. Condvar handoff
    let pair = Arc::new((Mutex::new(false), Condvar::new()));
    let pair2 = Arc::clone(&pair);
    let t = thread::spawn(move || {
        thread::sleep(Duration::from_millis(50));
        *pair2.0.lock().unwrap() = true;
        pair2.1.notify_one();
    });
    let (lock, cv) = &*pair;
    let ready = cv
        .wait_while(lock.lock().unwrap(), |ready| !*ready)
        .unwrap();
    println!("6. condvar woke, ready = {}", *ready);
    drop(ready);
    t.join().unwrap();

    // 7. Barrier
    let barrier = Arc::new(Barrier::new(3));
    let hs: Vec<_> = (0..3)
        .map(|_| {
            let b = Arc::clone(&barrier);
            thread::spawn(move || b.wait().is_leader())
        })
        .collect();
    let leaders = hs
        .into_iter()
        .map(|h| h.join().unwrap())
        .filter(|l| *l)
        .count();
    println!("7. barrier leaders: {leaders}");

    // 8. channels
    let (tx, rx) = mpsc::channel();
    for id in 0..3 {
        let tx = tx.clone();
        thread::spawn(move || tx.send(id * id).unwrap());
    }
    drop(tx);
    let mut got: Vec<i32> = rx.iter().collect();
    got.sort();
    println!("8. mpsc: {got:?}");

    let (tx, rx) = mpsc::sync_channel::<u32>(1);
    let prod = thread::spawn(move || {
        for i in 0..4 {
            tx.send(i).unwrap(); // blocks when the buffer (1) is full
        }
    });
    thread::sleep(Duration::from_millis(50));
    println!("   sync_channel: {:?}", rx.iter().collect::<Vec<_>>());
    prod.join().unwrap();

    // 9. OnceLock
    thread::scope(|s| {
        for i in 0..3 {
            s.spawn(move || {
                CONFIG.get_or_init(|| format!("initialised by someone ({i} may differ)"));
            });
        }
    });
    println!("9. OnceLock set exactly once: {}", CONFIG.get().is_some());

    // 10. thread-local
    COUNTER.with_borrow_mut(|c| *c += 1);
    let other = thread::spawn(|| COUNTER.with_borrow(|c| *c))
        .join()
        .unwrap();
    println!(
        "10. thread_local main = {}, other thread = {other}",
        COUNTER.with_borrow(|c| *c)
    );

    // 11. lock ordering: use try_lock to show a would-be deadlock safely
    let a = Mutex::new(1);
    let b = Mutex::new(2);
    let ga = a.lock().unwrap();
    println!(
        "11. second lock while first held, try_lock: {}",
        b.try_lock().is_ok()
    );
    drop(ga);

    // 12. File lock (1.89)
    let path = std::env::temp_dir().join("rust_guru_lock_demo.txt");
    let f = std::fs::File::create(&path).unwrap();
    f.lock().unwrap();
    let f2 = std::fs::File::open(&path).unwrap();
    println!(
        "12. File::try_lock on locked file: {:?}",
        f2.try_lock().is_ok()
    );
    f.unlock().unwrap();
    std::fs::remove_file(path).ok();
}
