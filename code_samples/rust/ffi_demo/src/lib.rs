//! A tiny C-callable library. Every `extern "C"` function here can be called from C.
//! See `demo.c` and `build.sh`.

use std::ffi::{CStr, CString, c_char, c_int};

// 1. Plain function: C types in, C types out. `#[unsafe(no_mangle)]` keeps the symbol name.
#[unsafe(no_mangle)]
pub extern "C" fn demo_add(a: c_int, b: c_int) -> c_int {
    a.wrapping_add(b)
}

// 2. A #[repr(C)] struct passed BY POINTER, with an out-parameter and an error code.
#[repr(C)]
pub struct Point {
    pub x: f64,
    pub y: f64,
}

#[unsafe(no_mangle)]
pub extern "C" fn demo_distance(p: *const Point, q: *const Point, out: *mut f64) -> c_int {
    if p.is_null() || q.is_null() || out.is_null() {
        return -1; // error code instead of a panic
    }
    // SAFETY: the caller promises valid, aligned pointers; we checked for null.
    unsafe {
        let (p, q) = (&*p, &*q);
        *out = ((p.x - q.x).powi(2) + (p.y - q.y).powi(2)).sqrt();
    }
    0
}

// 3. Strings: borrow a C string in, give an OWNED C string out, and provide the matching free.
#[unsafe(no_mangle)]
pub extern "C" fn demo_greet(name: *const c_char) -> *mut c_char {
    if name.is_null() {
        return std::ptr::null_mut();
    }
    // SAFETY: the caller passes a valid NUL-terminated string that lives for this call.
    let name = unsafe { CStr::from_ptr(name) }.to_string_lossy();
    match CString::new(format!("Hello, {name}!")) {
        Ok(s) => s.into_raw(), // ownership moves to the caller
        Err(_) => std::ptr::null_mut(),
    }
}

/// # Safety
/// `s` must come from `demo_greet` and must not be freed twice.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn demo_string_free(s: *mut c_char) {
    if !s.is_null() {
        // SAFETY: by the contract above, `s` came from CString::into_raw.
        drop(unsafe { CString::from_raw(s) });
    }
}

// 4. An OPAQUE handle: C sees only a pointer; Rust owns the real struct.
pub struct Counter {
    count: u64,
}

#[unsafe(no_mangle)]
pub extern "C" fn demo_counter_new() -> *mut Counter {
    Box::into_raw(Box::new(Counter { count: 0 }))
}

#[unsafe(no_mangle)]
pub extern "C" fn demo_counter_incr(c: *mut Counter) -> u64 {
    // SAFETY: the caller passes a live handle from demo_counter_new.
    let c = unsafe { c.as_mut() }.expect("null counter");
    c.count += 1;
    c.count
}

/// # Safety
/// `c` must come from `demo_counter_new` and must not be used afterwards.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn demo_counter_free(c: *mut Counter) {
    if !c.is_null() {
        // SAFETY: by contract, `c` came from Box::into_raw.
        drop(unsafe { Box::from_raw(c) });
    }
}

// 5. A callback from C into Rust: `extern "C" fn` pointer plus a user-data pointer.
pub type Visitor = extern "C" fn(value: c_int, user: *mut std::ffi::c_void);

#[unsafe(no_mangle)]
pub extern "C" fn demo_for_each(values: *const c_int, len: usize, visit: Visitor, user: *mut std::ffi::c_void) {
    // SAFETY: the caller guarantees `values` points to `len` readable ints.
    let slice = unsafe { std::slice::from_raw_parts(values, len) };
    for &v in slice {
        visit(v, user);
    }
}

// 6. Panics must never cross into C. An `extern "C"` function that panics ABORTS the process.
#[unsafe(no_mangle)]
pub extern "C" fn demo_panics() {
    panic!("boom");
}

// 7. Catch panics yourself and turn them into an error code.
#[unsafe(no_mangle)]
pub extern "C" fn demo_checked_divide(a: c_int, b: c_int, out: *mut c_int) -> c_int {
    let result = std::panic::catch_unwind(|| a / b); // panics when b == 0
    match result {
        Ok(v) if !out.is_null() => {
            // SAFETY: out is non-null and the caller promises it is writable.
            unsafe { *out = v };
            0
        }
        Ok(_) => -1,
        Err(_) => -2,
    }
}

// 8. A C-variadic DEFINITION (stable since Rust 1.99): `int demo_sum(int n, ...)`.
/// # Safety
/// The caller must pass exactly `n` further `int` arguments.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn demo_sum(n: c_int, mut args: ...) -> c_int {
    let mut total: c_int = 0;
    for _ in 0..n {
        // SAFETY: by the contract above there are `n` int arguments.
        total = total.wrapping_add(unsafe { args.next_arg::<c_int>() });
    }
    total
}
