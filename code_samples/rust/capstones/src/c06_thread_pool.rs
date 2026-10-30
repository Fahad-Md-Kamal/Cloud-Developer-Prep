//! Capstone 6: a thread pool.
//! Concepts: `Arc<Mutex<..>>`, channels, `Box<dyn FnOnce + Send>`, `Drop` for shutdown.

pub struct ThreadPool {
    // Workers plus the sending half of a job channel.
}

impl ThreadPool {
    /// Start `size` worker threads. Panic if `size == 0`.
    pub fn new(_size: usize) -> Self {
        todo!()
    }
    /// Queue a job. It runs on one of the workers.
    pub fn execute<F: FnOnce() + Send + 'static>(&self, _job: F) {
        todo!()
    }
}

// Stretch: implement Drop so that dropping the pool finishes queued jobs and joins every worker.

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::{
        Arc,
        atomic::{AtomicUsize, Ordering},
    };

    #[test]
    #[ignore = "c06: implement ThreadPool"]
    fn c06_runs_all_jobs_before_drop_returns() {
        let counter = Arc::new(AtomicUsize::new(0));
        {
            let pool = ThreadPool::new(4);
            for _ in 0..100 {
                let c = Arc::clone(&counter);
                pool.execute(move || {
                    c.fetch_add(1, Ordering::SeqCst);
                });
            }
        } // dropping the pool must wait for the jobs
        assert_eq!(counter.load(Ordering::SeqCst), 100);
    }

    #[test]
    #[ignore = "c06: implement ThreadPool"]
    #[should_panic]
    fn c06_zero_workers_panics() {
        let _ = ThreadPool::new(0);
    }
}
