//! Capstone 8: an arena (bump) allocator.
//! Concepts: `Layout`, alignment, raw pointers, `unsafe` with a safe API, lifetimes tied to `&self`,
//! `Drop`, `UnsafeCell`/`Cell`. Run your tests under Miri: `cargo +nightly miri test c08`.

pub struct Arena {
    // A block of bytes (for example `Vec<u8>` or an allocation from `std::alloc`) and a bump offset.
}

impl Arena {
    /// Create an arena with `capacity` bytes.
    pub fn with_capacity(_capacity: usize) -> Self {
        todo!()
    }
    /// Move `value` into the arena and return a reference that lives as long as `&self`.
    /// Return `None` when the arena is full. Respect `align_of::<T>()`.
    #[allow(clippy::mut_from_ref)]
    pub fn alloc<T>(&self, _value: T) -> Option<&mut T> {
        todo!("align the offset, check space, write, bump")
    }
    pub fn used(&self) -> usize {
        todo!()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    #[ignore = "c08: implement Arena"]
    fn c08_allocates_distinct_aligned_values() {
        let arena = Arena::with_capacity(1024);
        let a = arena.alloc(1u8).unwrap();
        let b = arena.alloc(2u64).unwrap();
        *a += 1;
        *b += 1;
        assert_eq!((*a, *b), (2, 3));
        assert_eq!((b as *mut u64 as usize) % align_of::<u64>(), 0);
    }

    #[test]
    #[ignore = "c08: implement Arena"]
    fn c08_full_arena_returns_none() {
        let arena = Arena::with_capacity(8);
        assert!(arena.alloc([0u8; 8]).is_some());
        assert!(arena.alloc(1u8).is_none());
    }
}
