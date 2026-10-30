//! Layout API: `Layout`, raw allocation, `size_of_val_raw`, enum tags, `repr(transparent)`,
//! a trait object's vtable-based size, and reading a packed field safely.
//! Run: cargo run --example layout_api

use std::alloc::{Layout, alloc, dealloc};
use std::fmt::Debug;
use std::mem::{align_of_val_raw, size_of, size_of_val, size_of_val_raw};

#[allow(dead_code)]
#[repr(C, packed)]
struct Packed {
    tag: u8,
    value: u32,
}

#[repr(transparent)]
struct Meters(f64);

#[allow(dead_code)]
enum Shape {
    Circle(f64),
    Rect(f64, f64),
}

#[allow(dead_code)]
#[repr(u8)]
enum Tagged {
    A(u32) = 1,
    B(u8) = 2,
}

fn main() {
    // Layout::new / array / from_size_align
    let l = Layout::new::<u64>();
    println!(
        "Layout::new::<u64>() -> size {} align {}",
        l.size(),
        l.align()
    );
    let arr = Layout::array::<u32>(10).unwrap();
    println!(
        "Layout::array::<u32>(10) -> size {} align {}",
        arr.size(),
        arr.align()
    );
    println!(
        "from_size_align(10, 3) is_err: {}",
        Layout::from_size_align(10, 3).is_err()
    );

    // Raw allocation with a Layout: you must free with the SAME layout.
    unsafe {
        let p = alloc(arr) as *mut u32;
        for i in 0..10 {
            p.add(i).write(i as u32 * i as u32);
        }
        println!("raw buffer[9] = {}", p.add(9).read());
        dealloc(p as *mut u8, arr);
    }

    // size_of_val_raw / align_of_val_raw on fat raw pointers
    let s: &[u32] = &[1, 2, 3];
    let d: &dyn Debug = &7_u16;
    unsafe {
        println!(
            "slice: size {} align {}; &dyn Debug(u16): size {} align {}",
            size_of_val_raw(s as *const [u32]),
            align_of_val_raw(s as *const [u32]),
            size_of_val_raw(d as *const dyn Debug),
            align_of_val_raw(d as *const dyn Debug)
        );
    }
    let boxed: Box<dyn Debug> = Box::new([0u8; 100]);
    println!(
        "size_of_val(&*Box<dyn Debug> of [u8;100]) = {}",
        size_of_val(&*boxed)
    );

    // enum layout
    println!(
        "Shape = {} (tag + two f64 = 24), Tagged(repr(u8)) = {}",
        size_of::<Shape>(),
        size_of::<Tagged>()
    );
    println!("Meters (transparent f64) = {}", size_of::<Meters>());

    // packed: copy the field out (by value) instead of taking a reference
    let p = Packed {
        tag: 1,
        value: 0xDEAD_BEEF,
    };
    let v = p.value; // a copy: fine
    println!(
        "packed value (copied) = {v:#x}, size {}",
        size_of::<Packed>()
    );
}
