//! Unsafe Rust: the five powers, safe abstractions over unsafe code, MaybeUninit, ManuallyDrop,
//! raw references, and a tiny Vec built from `NonNull` + `Layout`.
//! Run: cargo run --example unsafe_basics        (and under Miri: cargo +nightly miri run --example unsafe_basics)

use std::alloc::{self, Layout};
use std::marker::PhantomData;
use std::mem::{ManuallyDrop, MaybeUninit};
use std::ptr::{self, NonNull};

// 1. A safe abstraction: split_at_mut written with unsafe. The CONTRACT: the two halves never overlap.
fn my_split_at_mut<T>(slice: &mut [T], mid: usize) -> (&mut [T], &mut [T]) {
    let len = slice.len();
    assert!(mid <= len, "mid out of range");
    let ptr = slice.as_mut_ptr();
    // SAFETY: `mid <= len`, the halves [0, mid) and [mid, len) do not overlap, and both come from
    // the one exclusive borrow `slice`, so no other reference to them can exist.
    unsafe {
        (
            std::slice::from_raw_parts_mut(ptr, mid),
            std::slice::from_raw_parts_mut(ptr.add(mid), len - mid),
        )
    }
}

// 2. An unsafe fn states its contract in a `# Safety` section.
/// Returns the element at `index` without a bounds check.
///
/// # Safety
/// `index` must be less than `slice.len()`.
unsafe fn get_unchecked_demo<T>(slice: &[T], index: usize) -> &T {
    // SAFETY: the caller guarantees `index < slice.len()`.
    unsafe { &*slice.as_ptr().add(index) }
}

// 3. A minimal Vec: NonNull + PhantomData<T> + Layout, with Drop.
struct MiniVec<T> {
    ptr: NonNull<T>,
    cap: usize,
    len: usize,
    _owns: PhantomData<T>,
}

impl<T> MiniVec<T> {
    fn new() -> Self {
        assert!(
            size_of::<T>() != 0,
            "this demo does not handle zero-sized types"
        );
        MiniVec {
            ptr: NonNull::dangling(),
            cap: 0,
            len: 0,
            _owns: PhantomData,
        }
    }

    fn grow(&mut self) {
        let new_cap = if self.cap == 0 { 4 } else { self.cap * 2 };
        let new_layout = Layout::array::<T>(new_cap).expect("capacity overflow");
        let new_ptr = if self.cap == 0 {
            // SAFETY: new_layout has non-zero size (T is not a ZST and new_cap > 0).
            unsafe { alloc::alloc(new_layout) }
        } else {
            let old_layout = Layout::array::<T>(self.cap).unwrap();
            // SAFETY: self.ptr was allocated with old_layout; new size is non-zero.
            unsafe { alloc::realloc(self.ptr.as_ptr() as *mut u8, old_layout, new_layout.size()) }
        };
        self.ptr = NonNull::new(new_ptr as *mut T)
            .unwrap_or_else(|| alloc::handle_alloc_error(new_layout));
        self.cap = new_cap;
    }

    fn push(&mut self, value: T) {
        if self.len == self.cap {
            self.grow();
        }
        // SAFETY: len < cap after grow, so the slot is inside the allocation and uninitialized.
        unsafe { self.ptr.as_ptr().add(self.len).write(value) };
        self.len += 1;
    }

    fn pop(&mut self) -> Option<T> {
        if self.len == 0 {
            return None;
        }
        self.len -= 1;
        // SAFETY: slot `len` was initialized; we shrink len first so it is never read again.
        Some(unsafe { self.ptr.as_ptr().add(self.len).read() })
    }

    fn as_slice(&self) -> &[T] {
        // SAFETY: the first `len` elements are initialized, and the pointer is non-null and aligned
        // (dangling-but-aligned when len == 0).
        unsafe { std::slice::from_raw_parts(self.ptr.as_ptr(), self.len) }
    }
}

impl<T> Drop for MiniVec<T> {
    fn drop(&mut self) {
        while self.pop().is_some() {} // drop every element
        if self.cap != 0 {
            let layout = Layout::array::<T>(self.cap).unwrap();
            // SAFETY: allocated with this exact layout.
            unsafe { alloc::dealloc(self.ptr.as_ptr() as *mut u8, layout) };
        }
    }
}

// 4. MaybeUninit: build an array element by element without a dummy initial value.
fn squares() -> [u32; 5] {
    let mut arr: [MaybeUninit<u32>; 5] = [const { MaybeUninit::uninit() }; 5];
    for (i, slot) in arr.iter_mut().enumerate() {
        slot.write((i * i) as u32);
    }
    // SAFETY: every element was written above; MaybeUninit<u32> has the same layout as u32.
    unsafe { std::mem::transmute::<[MaybeUninit<u32>; 5], [u32; 5]>(arr) }
}

// 5. Raw references: `&raw const` makes a pointer to a packed field without creating a reference.
#[repr(C, packed)]
struct Packed {
    tag: u8,
    value: u32,
}

struct Noisy(&'static str);
impl Drop for Noisy {
    fn drop(&mut self) {
        println!("dropping {}", self.0);
    }
}

static mut COUNTER: u32 = 0; // edition 2024 denies *references* to it; use raw pointers

fn main() {
    let mut data = [1, 2, 3, 4, 5, 6];
    let (left, right) = my_split_at_mut(&mut data, 2);
    left[0] = 10;
    right[0] = 30;
    println!("split_at_mut: {data:?}");

    let v = [10, 20, 30];
    // SAFETY: 1 < 3.
    println!("get_unchecked_demo: {}", unsafe {
        get_unchecked_demo(&v, 1)
    });

    let mut mv = MiniVec::new();
    for i in 0..10 {
        mv.push(format!("item{i}"));
    }
    let last = mv.pop();
    println!(
        "MiniVec: len {} cap {} last {:?} slice[3] {}",
        mv.len,
        mv.cap,
        last,
        mv.as_slice()[3]
    );

    println!("MaybeUninit squares: {:?}", squares());

    let p = Packed {
        tag: 1,
        value: 0xCAFE,
    };
    let ptr = &raw const p.value;
    // SAFETY: ptr points into `p`, which is alive; read_unaligned handles the missing alignment.
    println!(
        "packed read via raw pointer: {:#x} (tag {})",
        unsafe { ptr.read_unaligned() },
        p.tag
    );

    // ManuallyDrop: suppress an automatic drop, then drop on purpose, exactly once.
    let mut a = ManuallyDrop::new(Noisy("manual"));
    let _b = Noisy("automatic");
    // SAFETY: `a` is never used again after this call.
    unsafe { ManuallyDrop::drop(&mut a) };

    // static mut through a raw pointer (the 2024-edition-safe way)
    // SAFETY: single-threaded here, so no data race.
    unsafe {
        let c = &raw mut COUNTER;
        *c += 1;
        println!("static mut COUNTER = {}", *c);
    }

    // The five powers in one place
    let x = 5;
    let rp = &x as *const i32;
    // 1) dereference a raw pointer  2) call an unsafe fn  3) access a static mut  4) impl an unsafe trait
    // 5) access a union field
    union IntOrFloat {
        i: u32,
        f: f32,
    }
    let u = IntOrFloat { f: 1.0 };
    // SAFETY: rp points to x; both union fields are plain 4-byte values with no invalid patterns.
    unsafe { println!("raw deref {}, union bits {:#x}", *rp, u.i) };
    let _ = ptr::eq(rp, &x);
}
