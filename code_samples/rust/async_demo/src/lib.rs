//! Small types used by the Concurrency & Async pages.
//! `cargo test` runs the normal tests; the loom model runs with
//! `RUSTFLAGS="--cfg loom" cargo test --release --lib loom_tests`.

#[cfg(loom)]
use loom::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
#[cfg(not(loom))]
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};

/// A flag plus data handoff: the writer publishes `data`, then sets `ready`.
pub struct Handoff {
    pub data: AtomicUsize,
    pub ready: AtomicBool,
}

impl Handoff {
    pub fn new() -> Self {
        Self { data: AtomicUsize::new(0), ready: AtomicBool::new(false) }
    }

    pub fn publish(&self, v: usize, publish_order: Ordering) {
        self.data.store(v, Ordering::Relaxed);
        self.ready.store(true, publish_order);
    }

    pub fn try_read(&self, read_order: Ordering) -> Option<usize> {
        if self.ready.load(read_order) {
            Some(self.data.load(Ordering::Relaxed))
        } else {
            None
        }
    }
}

impl Default for Handoff {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(all(test, not(loom)))]
mod tests {
    use super::*;

    #[test]
    fn single_thread_handoff() {
        let h = Handoff::new();
        assert_eq!(h.try_read(Ordering::Acquire), None);
        h.publish(7, Ordering::Release);
        assert_eq!(h.try_read(Ordering::Acquire), Some(7));
    }
}

#[cfg(all(test, loom))]
mod loom_tests {
    use super::*;
    use loom::sync::Arc;
    use loom::thread;

    fn run(publish: Ordering, read: Ordering) {
        loom::model(move || {
            let h = Arc::new(Handoff::new());
            let h2 = Arc::clone(&h);
            let t = thread::spawn(move || h2.publish(42, publish));
            if let Some(v) = h.try_read(read) {
                assert_eq!(v, 42, "saw ready=true but stale data");
            }
            t.join().unwrap();
        });
    }

    #[test]
    fn release_acquire_is_correct() {
        run(Ordering::Release, Ordering::Acquire);
    }

    #[test]
    #[should_panic(expected = "stale data")]
    fn relaxed_is_a_bug() {
        run(Ordering::Relaxed, Ordering::Relaxed);
    }
}
