//! Integers, floats, casts and conversions: where Rust is strict on purpose.
//! Run: cargo run --example numeric_semantics
//! Run: cargo run --release --example numeric_semantics   (overflow behaviour differs!)

use std::num::NonZeroU32;

fn main() {
    // 1. Overflow: explicit APIs say what you mean.
    let x: u8 = 250;
    println!("checked_add   = {:?}", x.checked_add(10)); // None on overflow
    println!("wrapping_add  = {}", x.wrapping_add(10)); // wraps around
    println!("saturating_add= {}", x.saturating_add(10)); // clamps at MAX
    println!("overflowing   = {:?}", x.overflowing_add(10)); // (wrapped, did_overflow)
    // `strict_add` always panics on overflow, even in release (stable since 1.91).
    let r = std::panic::catch_unwind(|| 250u8.strict_add(10));
    println!("strict_add panics = {}", r.is_err());

    // Plain `+` panics in debug builds and wraps in release builds.
    let big: u8 = std::hint::black_box(255);
    let r = std::panic::catch_unwind(|| big + 1);
    println!(
        "plain + panicked = {} (true in debug, false in release)",
        r.is_err()
    );

    // 2. `as` casts truncate or saturate silently. Prefer From/TryFrom.
    println!("300_i32 as u8    = {}", 300_i32 as u8); // truncates to 44
    println!("-1_i32 as u32    = {}", -1_i32 as u32); // reinterprets bits
    println!("3.99_f64 as i32  = {}", 3.99_f64 as i32); // truncates toward zero
    println!("1e20_f64 as i32  = {}", 1e20_f64 as i32); // saturates at i32::MAX
    println!("f64::NAN as i32  = {}", f64::NAN as i32); // 0
    println!("u8::try_from(300) = {:?}", u8::try_from(300_i32).is_err());
    println!("u64::from(7_u32)  = {}", u64::from(7_u32)); // lossless: From

    // 3. Floats: NaN breaks equality and ordering.
    let nan = f64::NAN;
    println!("NaN == NaN       = {}", nan == nan);
    println!("NaN < 1.0        = {}", nan < 1.0);
    let mut v: Vec<f64> = vec![3.2, 1.5, 2.7];
    v.sort_by(|a, b| a.total_cmp(b)); // f64 is PartialOrd, not Ord: use total_cmp
    println!("sorted floats    = {v:?}");
    println!("0.1 + 0.2        = {}", 0.1 + 0.2);

    // 4. char is a 4-byte Unicode scalar value, not a byte.
    println!(
        "size_of char = {}, '🦀' as u32 = {:#x}",
        size_of::<char>(),
        '🦀' as u32
    );

    // 5. NonZero types give the compiler a spare bit pattern ("niche").
    println!("size_of Option<u32>        = {}", size_of::<Option<u32>>());
    println!(
        "size_of Option<NonZeroU32> = {}",
        size_of::<Option<NonZeroU32>>()
    );
    println!("size_of Option<&u8>        = {}", size_of::<Option<&u8>>());
    println!(
        "size_of Option<Box<u8>>    = {}",
        size_of::<Option<Box<u8>>>()
    );

    // 6. assert_matches! (stable since 1.96) prints the value when a pattern fails.
    let value: Result<u8, String> = Ok(7);
    std::assert_matches!(value, Ok(n) if n > 5);
    println!("assert_matches! passed");
}
