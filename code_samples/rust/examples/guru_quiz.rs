//! Predict-the-output answers for the Guru Question Bank. Read each function, guess the
//! output, then run it. Run: cargo run --example guru_quiz

use std::cell::Cell;
use std::mem::size_of;
use std::num::NonZeroU32;
use std::rc::Rc;

struct Noisy(&'static str);
impl Drop for Noisy {
    fn drop(&mut self) {
        println!("drop {}", self.0);
    }
}
#[allow(dead_code)]
struct Pair {
    first: Noisy,
    second: Noisy,
}

fn q01_drop_order() {
    println!("-- Q1 drop order: locals vs fields vs temporaries");
    let _a = Noisy("local a");
    let _b = Noisy("local b");
    let _pair = Pair {
        first: Noisy("field 1"),
        second: Noisy("field 2"),
    };
    let _ = Noisy("underscore"); // dropped immediately: `_` does not bind
    println!("end of function");
}

fn q02_strings() {
    println!("-- Q2 strings");
    let s = "héllo";
    println!(
        "len {} chars {} bytes[1] {}",
        s.len(),
        s.chars().count(),
        s.as_bytes()[1]
    );
    println!("is_char_boundary(2) = {}", s.is_char_boundary(2));
}

#[allow(clippy::cast_nan_to_int)] // the NaN cast is the point of the question
fn q03_numbers() {
    println!("-- Q3 numbers");
    println!(
        "-7 / 2 = {}, -7 % 2 = {}, rem_euclid = {}",
        -7 / 2,
        -7 % 2,
        (-7i32).rem_euclid(2)
    );
    println!(
        "255u8 as i8 = {}, -1i32 as u32 = {}, 300i32 as u8 = {}",
        255u8 as i8, -1i32 as u32, 300i32 as u8
    );
    println!(
        "3.9 as i32 = {}, -3.9 as i32 = {}, NaN as i32 = {}, 1e20 as i32 = {}",
        3.9f64 as i32,
        -3.9f64 as i32,
        f64::NAN as i32,
        1e20f64 as i32
    );
    println!(
        "i32::MAX.wrapping_add(1) = {}, saturating_add = {:?}, checked_add = {:?}",
        i32::MAX.wrapping_add(1),
        i32::MAX.saturating_add(1),
        i32::MAX.checked_add(1)
    );
    println!("0.1 + 0.2 == 0.3 is {}", 0.1 + 0.2 == 0.3);
}

fn q04_laziness() {
    println!("-- Q4 laziness");
    let calls = Cell::new(0);
    let it = [1, 2, 3].iter().map(|x| {
        calls.set(calls.get() + 1);
        x * 2
    });
    println!("after map: calls = {}", calls.get());
    let v: Vec<i32> = it.collect();
    println!("after collect: calls = {}, v = {v:?}", calls.get());
    let first_big = [1, 2, 3, 4]
        .iter()
        .inspect(|_| calls.set(calls.get() + 100))
        .find(|&&x| x > 1);
    println!("find stops early: {first_big:?}, calls = {}", calls.get());
}

fn q05_sizes() {
    println!("-- Q5 sizes (64-bit)");
    println!(
        "&u8 = {}, Option<&u8> = {}, Box<i32> = {}, Option<Box<i32>> = {}",
        size_of::<&u8>(),
        size_of::<Option<&u8>>(),
        size_of::<Box<i32>>(),
        size_of::<Option<Box<i32>>>()
    );
    println!(
        "u32 = {}, Option<u32> = {}, Option<NonZeroU32> = {}",
        size_of::<u32>(),
        size_of::<Option<u32>>(),
        size_of::<Option<NonZeroU32>>()
    );
    println!(
        "&str = {}, &[u8] = {}, &dyn Send = {}, String = {}, Vec<u8> = {}",
        size_of::<&str>(),
        size_of::<&[u8]>(),
        size_of::<&dyn Send>(),
        size_of::<String>(),
        size_of::<Vec<u8>>()
    );
    println!(
        "() = {}, [u8; 0] = {}, Vec<()> cap = {}",
        size_of::<()>(),
        size_of::<[u8; 0]>(),
        Vec::<()>::with_capacity(3).capacity() == usize::MAX
    );
}

fn q06_rc() {
    println!("-- Q6 Rc counts");
    let a = Rc::new(5);
    let b = Rc::clone(&a);
    println!("strong = {}", Rc::strong_count(&a));
    drop(b);
    let w = Rc::downgrade(&a);
    println!(
        "strong = {}, weak = {}, upgrade ok = {}",
        Rc::strong_count(&a),
        Rc::weak_count(&a),
        w.upgrade().is_some()
    );
    drop(a);
    println!("after drop: upgrade ok = {}", w.upgrade().is_some());
}

fn q07_closures() {
    println!("-- Q7 closures");
    let mut c = 0;
    let mut inc = || c += 1;
    inc();
    inc();
    println!("c = {c}");
    let s = String::from("hi");
    let f = move || s.len();
    println!("f() = {}, f() = {}", f(), f());
    let fns: Vec<Box<dyn Fn() -> i32>> = (1..=3)
        .map(|i| Box::new(move || i * 10) as Box<dyn Fn() -> i32>)
        .collect();
    println!(
        "boxed closures: {:?}",
        fns.iter().map(|f| f()).collect::<Vec<_>>()
    );
}

fn q08_misc() {
    println!("-- Q8 misc");
    println!("split: {:?}", "a,b,,c".split(',').collect::<Vec<_>>());
    println!(
        "split_whitespace: {:?}",
        " a  b ".split_whitespace().collect::<Vec<_>>()
    );
    let x = 5;
    let x = x * 2;
    {
        let x = x + 1;
        println!("inner x = {x}");
    }
    println!("outer x = {x}");
    let a = [1, 2, 3];
    let b = a; // arrays of Copy types are Copy
    println!("a still usable: {}", a[0] + b[0]);
    let n = 7;
    let label = match n {
        k @ 1..=5 => format!("small {k}"),
        k @ (6 | 7) => format!("six-or-seven {k}"),
        _ => "other".to_string(),
    };
    println!("{label}");
    println!(
        "sum of empty: {}, product of empty: {}",
        [0i32; 0].iter().sum::<i32>(),
        [0i32; 0].iter().product::<i32>()
    );
    println!(
        "max_by_key ties pick the last: {:?}",
        ["aa", "bb", "c"].iter().max_by_key(|s| s.len())
    );
    println!(
        "min_by_key ties pick the first: {:?}",
        ["aa", "bb", "c", "d"].iter().min_by_key(|s| s.len())
    );
}

fn main() {
    q01_drop_order();
    q02_strings();
    q03_numbers();
    q04_laziness();
    q05_sizes();
    q06_rc();
    q07_closures();
    q08_misc();
}
