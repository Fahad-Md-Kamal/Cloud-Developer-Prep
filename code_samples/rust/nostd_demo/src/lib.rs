//! A tiny `no_std` library: ring buffer with fixed storage, no heap.
//! Builds for a bare-metal target:
//!     cargo build --release --target thumbv7em-none-eabihf
//! and tests on the host (std is available in tests):
//!     cargo test
#![no_std]

#[cfg(feature = "alloc")]
extern crate alloc;

/// Fixed-capacity ring buffer. `N` is the capacity, stored inline.
pub struct Ring<T: Copy, const N: usize> {
    buf: [Option<T>; N],
    head: usize,
    len: usize,
}

impl<T: Copy, const N: usize> Ring<T, N> {
    pub const fn new() -> Self {
        Self { buf: [None; N], head: 0, len: 0 }
    }

    /// Returns `Err(value)` when full (nothing is allocated, nothing is dropped).
    pub fn push(&mut self, value: T) -> Result<(), T> {
        if self.len == N {
            return Err(value);
        }
        let tail = (self.head + self.len) % N;
        self.buf[tail] = Some(value);
        self.len += 1;
        Ok(())
    }

    pub fn pop(&mut self) -> Option<T> {
        if self.len == 0 {
            return None;
        }
        let v = self.buf[self.head].take();
        self.head = (self.head + 1) % N;
        self.len -= 1;
        v
    }

    pub fn len(&self) -> usize {
        self.len
    }

    pub fn is_empty(&self) -> bool {
        self.len == 0
    }
}

impl<T: Copy, const N: usize> Default for Ring<T, N> {
    fn default() -> Self {
        Self::new()
    }
}

/// With the `alloc` feature we can also use `Vec`, still without `std`.
#[cfg(feature = "alloc")]
pub fn drain_all<T: Copy, const N: usize>(r: &mut Ring<T, N>) -> alloc::vec::Vec<T> {
    let mut out = alloc::vec::Vec::new();
    while let Some(v) = r.pop() {
        out.push(v);
    }
    out
}

/// Reads a hardware register. Volatile stops the compiler from removing or merging reads.
///
/// # Safety
/// `addr` must be a valid, aligned, readable register address.
pub unsafe fn read_reg(addr: *const u32) -> u32 {
    unsafe { core::ptr::read_volatile(addr) }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ring_wraps() {
        let mut r: Ring<u8, 3> = Ring::new();
        assert!(r.push(1).is_ok() && r.push(2).is_ok() && r.push(3).is_ok());
        assert_eq!(r.push(4), Err(4));
        assert_eq!(r.pop(), Some(1));
        r.push(5).unwrap();
        assert_eq!((r.pop(), r.pop(), r.pop(), r.pop()), (Some(2), Some(3), Some(5), None));
    }

    #[test]
    fn size_is_inline() {
        assert_eq!(size_of::<Ring<u8, 16>>(), 16 * 2 + 2 * size_of::<usize>());
    }
}
