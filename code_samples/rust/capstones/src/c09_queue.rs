//! Capstone 9: a lock-free (or lock-light) queue, checked with `loom`.
//! Start with a bounded single-producer single-consumer ring buffer using atomics
//! (`Release` on publish, `Acquire` on consume). Then try a multi-producer version.
//! Verify with loom: `cargo add loom --dev`, then run your model with `loom::model`.

pub struct Spsc<T> {
    // A fixed array of slots plus `head` and `tail` atomics.
    _marker: std::marker::PhantomData<T>,
}

impl<T> Spsc<T> {
    /// Capacity must be at least 1.
    pub fn new(_capacity: usize) -> Self {
        todo!()
    }
    /// Err gives the value back when the queue is full.
    pub fn push(&self, _value: T) -> Result<(), T> {
        todo!()
    }
    pub fn pop(&self) -> Option<T> {
        todo!()
    }
}

// SAFETY (to justify in your implementation): a single producer and a single consumer
// never touch the same slot at the same time because of the head/tail protocol.
unsafe impl<T: Send> Sync for Spsc<T> {}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Arc;

    #[test]
    #[ignore = "c09: implement Spsc"]
    fn c09_fifo_order_single_thread() {
        let q = Spsc::new(2);
        assert!(q.push(1).is_ok());
        assert!(q.push(2).is_ok());
        assert_eq!(q.push(3), Err(3));
        assert_eq!((q.pop(), q.pop(), q.pop()), (Some(1), Some(2), None));
    }

    #[test]
    #[ignore = "c09: implement Spsc"]
    fn c09_two_threads_see_every_item_once_in_order() {
        let q = Arc::new(Spsc::new(8));
        let producer = {
            let q = Arc::clone(&q);
            std::thread::spawn(move || {
                for i in 0..10_000u32 {
                    while q.push(i).is_err() {
                        std::hint::spin_loop();
                    }
                }
            })
        };
        let mut next = 0;
        while next < 10_000 {
            if let Some(v) = q.pop() {
                assert_eq!(v, next);
                next += 1;
            }
        }
        producer.join().unwrap();
    }
}
