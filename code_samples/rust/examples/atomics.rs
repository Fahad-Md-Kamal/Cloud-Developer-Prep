//! Atomics and memory ordering with std only.
//! Run: cargo run --release --example atomics
use std::hint;
use std::sync::atomic::{AtomicBool, AtomicPtr, AtomicU32, AtomicU64, AtomicUsize, Ordering};
use std::thread;

/// A minimal spinlock. Acquire on lock, Release on unlock.
struct SpinLock {
    locked: AtomicBool,
}

impl SpinLock {
    const fn new() -> Self {
        Self {
            locked: AtomicBool::new(false),
        }
    }
    fn lock(&self) {
        while self
            .locked
            .compare_exchange_weak(false, true, Ordering::Acquire, Ordering::Relaxed)
            .is_err()
        {
            hint::spin_loop();
        }
    }
    fn unlock(&self) {
        self.locked.store(false, Ordering::Release);
    }
}

static DATA: AtomicU64 = AtomicU64::new(0);
static READY: AtomicBool = AtomicBool::new(false);
static LOCK: SpinLock = SpinLock::new();
static RELAXED_COUNTER: AtomicUsize = AtomicUsize::new(0);

fn main() {
    // 1. Relaxed counter: atomic, but no ordering with other memory.
    thread::scope(|s| {
        for _ in 0..4 {
            s.spawn(|| {
                for _ in 0..100_000 {
                    RELAXED_COUNTER.fetch_add(1, Ordering::Relaxed);
                }
            });
        }
    });
    println!(
        "1. relaxed counter: {}",
        RELAXED_COUNTER.load(Ordering::Relaxed)
    );

    // 2. Release/Acquire handoff
    let h = thread::spawn(|| {
        while !READY.load(Ordering::Acquire) {
            hint::spin_loop();
        }
        DATA.load(Ordering::Relaxed)
    });
    DATA.store(42, Ordering::Relaxed);
    READY.store(true, Ordering::Release);
    println!("2. reader saw data = {}", h.join().unwrap());

    // 3. Spinlock protecting a non-atomic update
    let mut plain = 0u64;
    let p = &raw mut plain as usize;
    thread::scope(|s| {
        for _ in 0..4 {
            s.spawn(move || {
                for _ in 0..50_000 {
                    LOCK.lock();
                    // SAFETY: the spinlock gives exclusive access to `plain`.
                    unsafe { *(p as *mut u64) += 1 };
                    LOCK.unlock();
                }
            });
        }
    });
    println!("3. spinlock-protected counter: {plain}");

    // 4. CAS loop by hand: set to max
    let max = AtomicU64::new(10);
    let mut cur = max.load(Ordering::Relaxed);
    let new = 25;
    while cur < new {
        match max.compare_exchange_weak(cur, new, Ordering::Relaxed, Ordering::Relaxed) {
            Ok(_) => break,
            Err(actual) => cur = actual,
        }
    }
    println!("4. CAS-loop max: {}", max.load(Ordering::Relaxed));

    // 5. update / try_update (stable 1.95); `fetch_update` is now deprecated
    let a = AtomicU64::new(5);
    let prev = a.update(Ordering::SeqCst, Ordering::SeqCst, |x| x * 2);
    println!(
        "5. update returned previous {prev}, now {}",
        a.load(Ordering::SeqCst)
    );
    let r = a.try_update(Ordering::SeqCst, Ordering::SeqCst, |x| (x < 5).then_some(0));
    println!("   try_update refused (closure returned None): {r:?}");
    let r = a.try_update(Ordering::SeqCst, Ordering::SeqCst, |x| {
        (x > 5).then_some(x + 1)
    });
    println!(
        "   try_update applied: {r:?}, now {}",
        a.load(Ordering::SeqCst)
    );

    // 6. compare_exchange result values
    let c = AtomicUsize::new(1);
    println!(
        "6. CAS success: {:?}, failure: {:?}",
        c.compare_exchange(1, 2, Ordering::SeqCst, Ordering::SeqCst),
        c.compare_exchange(1, 3, Ordering::SeqCst, Ordering::SeqCst)
    );

    // 7. AtomicPtr
    let mut x = 10;
    let ptr = AtomicPtr::new(&mut x);
    println!("7. AtomicPtr points at {}", unsafe {
        *ptr.load(Ordering::Acquire)
    });

    // 8. from_mut views a plain integer as an atomic (stable 1.98 on the concrete types)
    let mut raw = 5u32;
    let view = AtomicU32::from_mut(&mut raw);
    view.fetch_add(1, Ordering::Relaxed);
    println!("8. from_mut view changed the u32: {raw}");

    println!(
        "9. size_of AtomicU64 = {}, align = {}",
        size_of::<AtomicU64>(),
        align_of::<AtomicU64>()
    );
}
