//! Rust CALLING C: libc functions through an `unsafe extern "C"` block (2024 edition syntax).
//! Run: cargo run

use std::ffi::{CStr, CString, c_char, c_int, c_void};

unsafe extern "C" {
    // `safe fn` states that calling it cannot cause UB, so no `unsafe` block is needed.
    pub safe fn abs(x: c_int) -> c_int;
    // These take pointers, so they stay unsafe to call.
    pub fn strlen(s: *const c_char) -> usize;
    pub fn qsort(base: *mut c_void, n: usize, size: usize, cmp: extern "C" fn(*const c_void, *const c_void) -> c_int);
    pub fn getenv(name: *const c_char) -> *const c_char;
}

extern "C" fn compare_ints(a: *const c_void, b: *const c_void) -> c_int {
    // SAFETY: qsort passes pointers to elements of the array we gave it (c_int).
    let (a, b) = unsafe { (*(a as *const c_int), *(b as *const c_int)) };
    a.cmp(&b) as c_int
}

fn main() {
    println!("abs(-7) = {}", abs(-7)); // safe fn: no unsafe block

    let s = CString::new("héllo").unwrap();
    // SAFETY: `s` is a valid NUL-terminated string.
    println!("strlen(\"héllo\") = {} (bytes, not characters)", unsafe { strlen(s.as_ptr()) });

    let mut v = [5, 3, 9, 1, 7];
    // SAFETY: pointer and size describe `v`; compare_ints matches the C signature.
    unsafe { qsort(v.as_mut_ptr() as *mut c_void, v.len(), size_of::<c_int>(), compare_ints) };
    println!("qsort -> {v:?}");

    let name = CString::new("HOME").unwrap();
    // SAFETY: valid C string; getenv returns NULL or a pointer to a NUL-terminated string.
    let home = unsafe { getenv(name.as_ptr()) };
    if home.is_null() {
        println!("HOME not set");
    } else {
        // SAFETY: non-null and NUL-terminated, valid until the environment changes.
        println!("HOME is set ({} bytes)", unsafe { CStr::from_ptr(home) }.to_bytes().len());
    }

    // Calling our own library from Rust the safe way: just a normal function.
    println!("demo_add(2, 3) = {}", ffi_demo::demo_add(2, 3));
}
