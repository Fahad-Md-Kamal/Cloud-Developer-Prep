//! Memory layout: size, alignment, field reordering, repr, niches, fat pointers, ZSTs.
//! Run: cargo run --example memory_layout

use std::marker::PhantomData;
use std::mem::{align_of, offset_of, size_of, size_of_val};
use std::rc::Rc;

#[allow(dead_code)]
struct Reordered {
    a: u8,
    b: u32,
    c: u8,
    d: u16,
}

#[allow(dead_code)]
#[repr(C)]
struct CLayout {
    a: u8,
    b: u32,
    c: u8,
    d: u16,
}

#[allow(dead_code)]
#[repr(C, packed)]
struct Packed {
    a: u8,
    b: u32,
}

#[allow(dead_code)]
#[repr(align(64))]
struct CacheLine(u8);

#[allow(dead_code)]
#[repr(u8)]
enum Status {
    Ok = 0,
    Warn = 1,
    Fail = 2,
}

#[allow(dead_code)]
enum Message {
    Quit,
    Move { x: i32, y: i32 },
    Write(String),
}

struct Empty;

// ?Sized lets a generic parameter be a dynamically sized type (str, [T], dyn Trait).
fn byte_len<T: ?Sized>(v: &T) -> usize {
    size_of_val(v)
}

fn main() {
    println!("-- field order and padding");
    println!("Reordered (default repr): size {} align {}", size_of::<Reordered>(), align_of::<Reordered>());
    println!("CLayout   (repr(C))      : size {} align {}", size_of::<CLayout>(), align_of::<CLayout>());
    println!(
        "CLayout offsets: a={} b={} c={} d={}",
        offset_of!(CLayout, a),
        offset_of!(CLayout, b),
        offset_of!(CLayout, c),
        offset_of!(CLayout, d)
    );
    println!("Packed: size {} align {}", size_of::<Packed>(), align_of::<Packed>());
    println!("CacheLine: size {} align {}", size_of::<CacheLine>(), align_of::<CacheLine>());

    println!("-- primitive sizes");
    println!(
        "u8={} u16={} u32={} u64={} u128={} usize={} char={} bool={} ()={}",
        size_of::<u8>(), size_of::<u16>(), size_of::<u32>(), size_of::<u64>(),
        size_of::<u128>(), size_of::<usize>(), size_of::<char>(), size_of::<bool>(), size_of::<()>()
    );

    println!("-- enums");
    println!("Status (repr(u8)): {}", size_of::<Status>());
    println!("Message (String payload is the biggest): {}", size_of::<Message>());
    println!("String={} Vec<u8>={}", size_of::<String>(), size_of::<Vec<u8>>());

    println!("-- niches");
    println!("Option<u32>={} Option<NonZeroU32>={}", size_of::<Option<u32>>(), size_of::<Option<std::num::NonZeroU32>>());
    println!("Option<bool>={} Option<Option<bool>>={}", size_of::<Option<bool>>(), size_of::<Option<Option<bool>>>());
    println!("Option<char>={} Option<&u8>={} Option<Box<u8>>={}", size_of::<Option<char>>(), size_of::<Option<&u8>>(), size_of::<Option<Box<u8>>>());
    println!("Option<String>={} Option<Vec<u8>>={}", size_of::<Option<String>>(), size_of::<Option<Vec<u8>>>());

    println!("-- thin and fat pointers");
    println!("&u8={} Box<u8>={} Rc<u8>={}", size_of::<&u8>(), size_of::<Box<u8>>(), size_of::<Rc<u8>>());
    println!("&[u8]={} &str={} Box<[u8]>={} Rc<str>={}", size_of::<&[u8]>(), size_of::<&str>(), size_of::<Box<[u8]>>(), size_of::<Rc<str>>());
    println!("&dyn Debug={} Box<dyn Debug>={}", size_of::<&dyn std::fmt::Debug>(), size_of::<Box<dyn std::fmt::Debug>>());
    println!("fn pointer={} closure(no capture)={}", size_of::<fn(i32) -> i32>(), size_of_val(&|x: i32| x + 1));
    let n = 7;
    let capturing = move |x: i32| x + n;
    println!("closure capturing one i32={}", size_of_val(&capturing));

    println!("-- dynamically sized values (size_of_val)");
    let arr = [1u32, 2, 3, 4];
    println!("[u32; 4] = {}, as &[u32] = {}, str \"héllo\" = {}", byte_len(&arr), byte_len(&arr[..]), byte_len("héllo"));

    println!("-- zero-sized types");
    println!("Empty={} PhantomData<String>={} [u8; 0]={}", size_of::<Empty>(), size_of::<PhantomData<String>>(), size_of::<[u8; 0]>());
    let mut units: Vec<()> = Vec::new();
    for _ in 0..1000 {
        units.push(());
    }
    println!("Vec<()> with 1000 items: len={} capacity={} (never allocates)", units.len(), units.capacity());
}
