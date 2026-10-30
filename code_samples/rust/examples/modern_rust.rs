//! Modern Rust: one small, runnable example per notable change from 1.85 to 1.99.
//! Run: cargo run --example modern_rust
//! Needs Rust 1.99 or newer and the 2024 edition (see Cargo.toml).

use std::cell::Cell;
use std::collections::{BTreeMap, HashMap, VecDeque};
use std::fmt;
use std::future::Future;
use std::num::NonZero;
use std::pin::pin;
use std::sync::RwLock;
use std::sync::atomic::{AtomicU32, Ordering};
use std::task::{Context, Poll, Waker};

fn section(title: &str) {
    println!("\n== {title}");
}

/// Run a future to completion without a runtime. Works only for futures that never wait.
fn block_on<F: Future>(fut: F) -> F::Output {
    let mut fut = pin!(fut);
    let mut cx = Context::from_waker(Waker::noop()); // Waker::noop: 1.85
    loop {
        if let Poll::Ready(v) = fut.as_mut().poll(&mut cx) {
            return v;
        }
    }
}

// ---------------------------------------------------------------- 1.85
async fn apply_async(f: impl AsyncFn(i32) -> i32, x: i32) -> i32 {
    f(x).await
}

fn v1_85() {
    section("1.85: async closures, midpoint, fn_addr_eq");
    let offset = 10;
    // An async closure can borrow from its environment across the await point.
    let r = block_on(apply_async(async |x| x + offset, 5));
    println!("async closure result: {r}");
    println!(
        "u8::midpoint(250, 254) = {} (no overflow)",
        250u8.midpoint(254)
    );
    fn a() {}
    fn b() {}
    println!(
        "fn_addr_eq(a, a) = {}",
        std::ptr::fn_addr_eq(a as fn(), a as fn())
    );
    println!(
        "fn_addr_eq(a, b) = {}",
        std::ptr::fn_addr_eq(a as fn(), b as fn())
    );
}

// ---------------------------------------------------------------- 1.86
trait Animal {
    fn name(&self) -> String;
}
trait Dog: Animal {}
struct Rex;
impl Animal for Rex {
    fn name(&self) -> String {
        "Rex".into()
    }
}
impl Dog for Rex {}

fn v1_86() {
    section("1.86: trait upcasting, get_disjoint_mut, pop_if, black_box");
    let dog: Box<dyn Dog> = Box::new(Rex);
    let animal: Box<dyn Animal> = dog; // upcast to a supertrait object
    println!("upcast: {}", animal.name());

    let mut v = vec![1, 2, 3, 4];
    if let Ok([a, b]) = v.get_disjoint_mut([0, 3]) {
        std::mem::swap(a, b);
    }
    println!("get_disjoint_mut swap: {v:?}");
    println!(
        "overlap is an error: {:?}",
        v.get_disjoint_mut([1, 1]).is_err()
    );

    let popped = v.pop_if(|last| *last == 1);
    println!("pop_if: {popped:?}, left {v:?}");
    println!("black_box: {}", std::hint::black_box(21) * 2);
}

// ---------------------------------------------------------------- 1.87
trait Source {
    // `use<..>` lists exactly which generics the returned type captures (`Self` must be named).
    fn items<'a>(&'a self) -> impl Iterator<Item = u32> + use<'a, Self>;
}
struct Evens(Vec<u32>);
impl Source for Evens {
    fn items<'a>(&'a self) -> impl Iterator<Item = u32> + use<'a> {
        self.0.iter().copied().filter(|n| n % 2 == 0)
    }
}

fn v1_87() {
    section("1.87: precise capturing, extract_if, is_multiple_of, split_off, pipe");
    let e = Evens(vec![1, 2, 3, 4, 6]);
    println!("precise capturing: {:?}", e.items().collect::<Vec<_>>());

    let mut v: Vec<i32> = (1..=8).collect();
    let evens: Vec<i32> = v.extract_if(.., |x| *x % 2 == 0).collect();
    println!("extract_if: removed {evens:?}, left {v:?}");

    println!("12.is_multiple_of(4) = {}", 12u32.is_multiple_of(4));
    println!(
        "1u32.unbounded_shl(40) = {} (no panic)",
        1u32.unbounded_shl(40)
    );

    let mut data: &[i32] = &[1, 2, 3, 4];
    let first = data.split_off_first();
    println!("split_off_first: {first:?}, rest {data:?}");

    use std::io::{Read, Write};
    let (mut rx, mut tx) = std::io::pipe().expect("pipe");
    tx.write_all(b"hello pipe").unwrap();
    drop(tx);
    let mut s = String::new();
    rx.read_to_string(&mut s).unwrap();
    println!("io::pipe: {s}");
}

// ---------------------------------------------------------------- 1.88
fn v1_88() {
    section("1.88: let chains, Cell::update, extract_if on maps, as_chunks");
    let input = ["7", "x", "12"];
    for s in input {
        // let chains: mix `let` and boolean conditions with && (2024 edition only)
        if let Ok(n) = s.parse::<i32>()
            && n > 10
            && let Some(sq) = n.checked_mul(n)
        {
            println!("{s}: big number, square {sq}");
        } else {
            println!("{s}: skipped");
        }
    }
    let c = Cell::new(5);
    c.update(|x| x * 2);
    println!("Cell::update: {}", c.get());

    let mut m: HashMap<i32, &str> = HashMap::from([(1, "a"), (2, "b"), (3, "c")]);
    let mut odd: Vec<_> = m.extract_if(|k, _| k % 2 == 1).collect();
    odd.sort();
    println!(
        "HashMap::extract_if removed {odd:?}, left {} item(s)",
        m.len()
    );

    let r = std::hint::select_unpredictable(std::hint::black_box(true), 1, 2);
    println!("select_unpredictable: {r}");
    let (chunks, rest) = [1, 2, 3, 4, 5, 6, 7].as_chunks::<3>();
    println!("as_chunks::<3>: {chunks:?} rest {rest:?}");
    #[cfg(true)]
    println!("#[cfg(true)] is allowed");
}

// ---------------------------------------------------------------- 1.89
fn first_n<const N: usize>(v: &[i32]) -> [i32; N] {
    std::array::from_fn(|i| v[i])
}

#[repr(u128)]
#[allow(dead_code)]
enum Big {
    A = 1,
    B = u64::MAX as isize as u128,
}

fn v1_89() {
    section("1.89: inferred const args, Result::flatten, File::lock, repr(u128)");
    let a: [i32; _] = [10, 20, 30]; // length inferred
    let b: [i32; 2] = first_n(&[1, 2, 3, 4]); // N is inferred from the annotation
    let c: [i32; 3] = first_n::<_>(&[9, 8, 7, 6]); // explicit `_` const argument, N = 3 from the type
    println!("inferred length: {}, {b:?}, {c:?}", a.len());

    let nested: Result<Result<i32, String>, String> = Ok(Err("inner".into()));
    println!("Result::flatten: {:?}", nested.flatten());

    let path = std::env::temp_dir().join("modern_rust_lock_demo.txt");
    let f = std::fs::File::create(&path).unwrap();
    f.lock().unwrap();
    let other = std::fs::File::open(&path).unwrap(); // a second handle to the same file
    println!(
        "second handle try_lock: {:?}",
        other.try_lock().map_err(|e| e.to_string())
    );
    f.unlock().unwrap();
    println!("after unlock, try_lock ok: {}", other.try_lock().is_ok());
    std::fs::remove_file(&path).ok();
    println!("size_of::<Big>() = {}", size_of::<Big>());
}

// ---------------------------------------------------------------- 1.90
fn v1_90() {
    section("1.90: checked_sub_signed (lld default linker is a toolchain change)");
    println!(
        "5u32.checked_sub_signed(-3) = {:?}",
        5u32.checked_sub_signed(-3)
    );
    println!(
        "5u32.checked_sub_signed(9) = {:?}",
        5u32.checked_sub_signed(9)
    );
}

// ---------------------------------------------------------------- 1.91
fn v1_91() {
    section("1.91: strict_*, Duration::from_mins, BTreeMap::extract_if, iter::chain, ...");
    println!("5u8.strict_add(3) = {}", 5u8.strict_add(3));
    std::panic::set_hook(Box::new(|_| {})); // keep the demo output quiet
    let r = std::panic::catch_unwind(|| 250u8.strict_add(10));
    let _ = std::panic::take_hook();
    println!("250u8.strict_add(10) panics: {}", r.is_err());
    println!(
        "Duration::from_mins(90) = {:?}",
        std::time::Duration::from_mins(90)
    );

    let mut m: BTreeMap<i32, char> = [(1, 'a'), (2, 'b'), (3, 'c')].into();
    let removed: Vec<_> = m.extract_if(.., |k, _| *k >= 2).collect();
    println!("BTreeMap::extract_if: {removed:?}, left {m:?}");

    let both: Vec<_> = std::iter::chain([1, 2], [3]).collect();
    println!("iter::chain: {both:?}");
    let reps: [&str; 3] = std::array::repeat("ab");
    println!("array::repeat: {reps:?}");
    println!(
        "PathBuf::add_extension: {:?}",
        std::path::PathBuf::from("archive.tar").with_added_extension("gz")
    );
    println!(
        "Ipv4Addr::from_octets: {}",
        std::net::Ipv4Addr::from_octets([192, 168, 0, 1])
    );
    println!(
        "floor_char_boundary(\"héllo\", 2) = {}",
        "héllo".floor_char_boundary(2)
    );
}

// ---------------------------------------------------------------- 1.92
fn v1_92() {
    section("1.92: RwLockWriteGuard::downgrade, new_zeroed, insert_entry");
    let lock = RwLock::new(1);
    let mut w = lock.write().unwrap();
    *w += 1;
    let r = std::sync::RwLockWriteGuard::downgrade(w); // no gap where another writer sneaks in
    println!("downgraded to a read guard, value {}", *r);
    drop(r);

    // SAFETY: all-zero bits are a valid u64.
    let z = unsafe { Box::<u64>::new_zeroed().assume_init() };
    println!("Box::new_zeroed: {z}");

    let mut m: BTreeMap<&str, i32> = BTreeMap::new();
    let e = m.entry("k").insert_entry(7);
    println!("BTreeMap entry insert_entry: {}={}", e.key(), e.get());
}

// ---------------------------------------------------------------- 1.93
fn v1_93() {
    section("1.93: as_array, pop_front_if, fmt::from_fn, from_nanos_u128");
    let s: &[i32] = &[1, 2, 3];
    println!("<[T]>::as_array: {:?}", s.as_array::<3>());
    println!("wrong length: {:?}", s.as_array::<2>());

    let mut q: VecDeque<i32> = VecDeque::from([1, 2, 3]);
    println!("pop_front_if(>0): {:?}", q.pop_front_if(|x| *x > 0));

    let shown = std::fmt::from_fn(|f: &mut fmt::Formatter<'_>| write!(f, "built without a struct"));
    println!("fmt::from_fn: {shown}");
    println!(
        "from_nanos_u128: {:?}",
        std::time::Duration::from_nanos_u128(1_500_000_000)
    );
}

// ---------------------------------------------------------------- 1.94
fn v1_94() {
    section("1.94: array_windows, LazyLock::get/force_mut, next_if_map, constants");
    let v = [1, 2, 4, 7, 11];
    let diffs: Vec<i32> = v.array_windows().map(|[a, b]| b - a).collect();
    println!("array_windows diffs: {diffs:?}");

    let mut lazy = std::sync::LazyLock::new(|| vec![1, 2]);
    println!(
        "LazyLock::get before use: {:?}",
        std::sync::LazyLock::get(&lazy)
    );
    std::sync::LazyLock::force_mut(&mut lazy).push(3);
    println!("after force_mut: {:?}", *lazy);

    let mut it = ["10", "20", "x"].iter().peekable();
    let a = it.next_if_map(|s| s.parse::<i32>().ok().ok_or(s));
    println!("next_if_map: {a:?}");
    println!("GOLDEN_RATIO = {:.5}", std::f64::consts::GOLDEN_RATIO);
}

// ---------------------------------------------------------------- 1.95
#[derive(Debug)]
enum Msg {
    Num(i32),
    Text(String),
}

#[cold]
fn slow() -> i32 {
    -1
}

fn v1_95() {
    section("1.95: if let guards, cfg_select!, core::range, cold_path, push_mut, atomics");
    for m in [Msg::Num(7), Msg::Num(-3), Msg::Text("hi".into())] {
        let label = match m {
            Msg::Num(n)
                if let Some(d) = n.checked_sub(5)
                    && d > 0 =>
            {
                format!("num above 5 by {d}")
            }
            Msg::Num(n) => format!("other num {n}"),
            Msg::Text(ref s) if let Ok(n) = s.parse::<i32>() => format!("numeric text {n}"),
            Msg::Text(s) => format!("text {s}"),
        };
        println!("{label}");
    }

    let which = std::cfg_select! {
        unix => "unix",
        windows => "windows",
        _ => "other",
    };
    println!("cfg_select!: {which}");

    let r = std::range::Range { start: 2, end: 5 };
    let copy = r; // new range types are Copy
    println!(
        "core::range::Range is Copy: {r:?} {copy:?}, sum = {}",
        r.into_iter().sum::<i32>()
    );

    let x = std::hint::black_box(0);
    if x != 0 {
        std::hint::cold_path();
        println!("{}", slow());
    }

    let mut v = vec![1];
    *v.push_mut(2) += 40;
    println!("Vec::push_mut: {v:?}");

    let n = AtomicU32::new(5);
    let old = n.update(Ordering::SeqCst, Ordering::SeqCst, |x| x * 3);
    println!("atomic update: old {old}, now {}", n.load(Ordering::SeqCst));
    println!(
        "bool::try_from(1) = {:?}, try_from(2) is err = {}",
        bool::try_from(1),
        bool::try_from(2).is_err()
    );
}

// ---------------------------------------------------------------- 1.96
fn v1_96() {
    section("1.96: assert_matches!, NonZero ranges, core::range");
    let r: Result<i32, String> = Ok(4);
    std::assert_matches!(r, Ok(n) if n > 3);
    println!("assert_matches! passed");
    let sum: u32 = (NonZero::new(1u32).unwrap()..NonZero::new(4u32).unwrap())
        .map(|n| n.get())
        .sum();
    println!("range of NonZero: sum {sum}");
    let from = std::range::RangeFrom { start: 5 };
    println!(
        "core::range::RangeFrom first three: {:?}",
        from.into_iter().take(3).collect::<Vec<_>>()
    );
}

// ---------------------------------------------------------------- 1.97
fn v1_97() {
    section("1.97: bit helpers (highest_one, bit_width, isolate_*)");
    let n = 0b0010_1100u8;
    println!(
        "{n:#010b}: highest_one {:?}, lowest_one {:?}",
        n.highest_one(),
        n.lowest_one()
    );
    println!(
        "bit_width {}, isolate_highest_one {:#010b}, isolate_lowest_one {:#010b}",
        n.bit_width(),
        n.isolate_highest_one(),
        n.isolate_lowest_one()
    );
}

// ---------------------------------------------------------------- 1.98
fn v1_98() {
    section("1.98: bool::ok_or, map_or_default, substr_range, strip_circumfix, algebraic ops");
    println!("true.ok_or(\"no\") = {:?}", true.ok_or("no"));
    println!("false.ok_or(\"no\") = {:?}", false.ok_or("no"));
    println!(
        "Some(\"abc\") map_or_default len: {}",
        Some("abc").map_or_default(|s| s.len())
    );
    let none: Option<&str> = None;
    println!(
        "None map_or_default len: {}",
        none.map_or_default(|s| s.len())
    );

    let text = "hello big world";
    let word = &text[6..9];
    println!("substr_range: {:?}", text.substr_range(word));
    println!("strip_circumfix: {:?}", "[abc]".strip_circumfix("[", "]"));
    println!(
        "algebraic_add (fast-math style): {}",
        0.1f64.algebraic_add(0.2)
    );

    let mut raw = 5u32;
    let a = AtomicU32::from_mut(&mut raw); // no other thread can see `raw`, so this is safe
    a.fetch_add(1, Ordering::Relaxed);
    println!("Atomic::from_mut: {raw}");
}

// ---------------------------------------------------------------- 1.99
fn v1_99() {
    section("1.99: Vec::into_parts, retain_back, c-variadic definitions, LocalKey::update, ...");
    let v = vec![1u8, 2, 3];
    let (ptr, len, cap) = v.into_parts();
    // SAFETY: the parts come straight from `into_parts`.
    let v = unsafe { Vec::from_parts(ptr, len, cap) };
    println!("into_parts / from_parts round trip: {v:?}");

    let mut q: VecDeque<i32> = (1..=6).collect();
    q.retain_back(2); // keep only the last 2 elements
    println!("VecDeque::retain_back(2): {q:?}");

    let sum = unsafe { sum_ints(3, 10, 20, 30) };
    println!("c-variadic fn defined in Rust: {sum}");

    println!(
        "String::from_utf8_lossy_owned: {}",
        String::from_utf8_lossy_owned(vec![104, 105, 0xFF])
    );
    for x in Box::new([1, 2, 3]) {
        print!("Box<[T; N]> into_iter: {x} ");
    }
    println!();
    thread_local! { static COUNTER: Cell<u32> = const { Cell::new(1) }; }
    COUNTER.update(|c| c + 41);
    println!("LocalKey<Cell<T>>::update: {}", COUNTER.get());
    println!("size_of_val_raw is stable: {}", unsafe {
        std::mem::size_of_val_raw(&[0u16; 4] as *const [u16])
    });
}

/// A C-variadic function written in Rust (stable in 1.99).
///
/// # Safety
/// The caller passes `count` further `i32` arguments.
unsafe extern "C" fn sum_ints(count: i32, mut args: ...) -> i32 {
    let mut total = 0;
    for _ in 0..count {
        total += unsafe { args.next_arg::<i32>() };
    }
    total
}

fn main() {
    println!("rustc features by release, run on the installed stable toolchain");
    v1_85();
    v1_86();
    v1_87();
    v1_88();
    v1_89();
    v1_90();
    v1_91();
    v1_92();
    v1_93();
    v1_94();
    v1_95();
    v1_96();
    v1_97();
    v1_98();
    v1_99();
}
