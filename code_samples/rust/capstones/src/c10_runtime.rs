//! Capstone 10: a tiny async runtime.
//! Concepts: `Future`, `Poll`, `Context`, `Waker` (build one with `std::task::Wake`),
//! `Pin<Box<dyn Future>>`, a task queue, a timer. Std only.

use std::future::Future;

/// Run a future to completion on the current thread, parking the thread until woken.
pub fn block_on<F: Future>(_fut: F) -> F::Output {
    todo!("build a Waker that unparks this thread; poll in a loop")
}

/// A single-threaded executor that runs many tasks.
#[derive(Default)]
pub struct Executor {
    // A queue of tasks (pinned boxed futures plus a way to re-queue them when woken).
}

impl Executor {
    pub fn spawn(&mut self, _fut: impl Future<Output = ()> + 'static) {
        todo!()
    }
    /// Run until every spawned task has finished.
    pub fn run(&mut self) {
        todo!()
    }
}

/// A future that completes after `duration` (stretch: share one timer thread).
pub fn sleep(_duration: std::time::Duration) -> impl Future<Output = ()> {
    std::future::ready(()) // placeholder so the skeleton compiles; replace with a real timer
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::{cell::RefCell, rc::Rc};

    #[test]
    #[ignore = "c10: implement block_on"]
    fn c10_block_on_returns_value() {
        assert_eq!(block_on(async { 1 + 2 }), 3);
    }

    #[test]
    #[ignore = "c10: implement Executor"]
    fn c10_runs_every_task() {
        let log = Rc::new(RefCell::new(Vec::new()));
        let mut ex = Executor::default();
        for i in 0..3 {
            let log = Rc::clone(&log);
            ex.spawn(async move {
                log.borrow_mut().push(i);
            });
        }
        ex.run();
        assert_eq!(log.borrow().len(), 3);
    }

    #[test]
    #[ignore = "c10: implement sleep"]
    fn c10_sleep_waits() {
        let start = std::time::Instant::now();
        block_on(sleep(std::time::Duration::from_millis(50)));
        assert!(start.elapsed() >= std::time::Duration::from_millis(50));
    }
}
