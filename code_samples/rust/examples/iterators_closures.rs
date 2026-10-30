//! Iterators and closures: laziness, custom iterators, Fn/FnMut/FnOnce, returning closures.
//! Run: cargo run --example iterators_closures

use std::collections::HashMap;

// A custom iterator: implement `next`, get ~70 adapter methods for free.
struct Countdown(u32);
impl Iterator for Countdown {
    type Item = u32;
    fn next(&mut self) -> Option<u32> {
        if self.0 == 0 {
            None
        } else {
            self.0 -= 1;
            Some(self.0 + 1)
        }
    }
}

// A collection that can be iterated by reference.
struct Playlist {
    songs: Vec<String>,
}
impl<'a> IntoIterator for &'a Playlist {
    type Item = &'a String;
    type IntoIter = std::slice::Iter<'a, String>;
    fn into_iter(self) -> Self::IntoIter {
        self.songs.iter()
    }
}

fn evens_squared(v: &[i32]) -> impl Iterator<Item = i32> + '_ {
    v.iter().filter(|x| **x % 2 == 0).map(|x| x * x)
}

fn make_adder(n: i32) -> impl Fn(i32) -> i32 {
    move |x| x + n
}
fn make_boxed(kind: &str) -> Box<dyn Fn(i32) -> i32> {
    match kind {
        "double" => Box::new(|x| x * 2),
        _ => Box::new(|x| x),
    }
}

fn call_twice<F: FnMut()>(mut f: F) {
    f();
    f();
}
fn call_once<F: FnOnce() -> String>(f: F) -> String {
    f()
}

fn main() {
    // 1. Iterators are LAZY: nothing runs until something consumes them.
    let it = (1..=5).map(|x| {
        println!("  mapping {x}");
        x * 10
    });
    println!("built the iterator, nothing printed yet");
    let first_two: Vec<i32> = it.take(2).collect();
    println!("collected {first_two:?} (only 2 items were mapped)");

    // 2. Common adapters and consumers.
    let v = vec![1, 2, 3, 4, 5, 6];
    println!(
        "evens squared = {:?}",
        evens_squared(&v).collect::<Vec<_>>()
    );
    println!(
        "sum={} product={} max={:?}",
        v.iter().sum::<i32>(),
        v.iter().product::<i32>(),
        v.iter().max()
    );
    println!(
        "fold  = {}",
        v.iter().fold(String::new(), |acc, n| acc + &n.to_string())
    );
    println!(
        "zip   = {:?}",
        v.iter().zip("abc".chars()).collect::<Vec<_>>()
    );
    println!(
        "windows = {:?}",
        v.windows(3)
            .map(|w| w.iter().sum::<i32>())
            .collect::<Vec<_>>()
    );
    println!("chunks  = {:?}", v.chunks(4).collect::<Vec<_>>());
    println!(
        "flat_map = {:?}",
        ["ab", "cd"]
            .iter()
            .flat_map(|s| s.chars())
            .collect::<String>()
    );
    println!(
        "scan  = {:?}",
        v.iter()
            .scan(0, |s, x| {
                *s += x;
                Some(*s)
            })
            .collect::<Vec<_>>()
    );
    println!(
        "rev/step_by = {:?}",
        (0..10).rev().step_by(3).collect::<Vec<_>>()
    );
    println!(
        "any/all/position = {} {} {:?}",
        v.iter().any(|x| *x > 5),
        v.iter().all(|x| *x > 0),
        v.iter().position(|x| *x == 4)
    );
    let (small, big): (Vec<i32>, Vec<i32>) = v.iter().partition(|x| **x < 4);
    println!("partition = {small:?} {big:?}");

    // 3. collect() builds many types, chosen by the annotation.
    let m: HashMap<_, _> = ["a", "bb", "ccc"].iter().map(|s| (*s, s.len())).collect();
    let mut keys: Vec<_> = m.keys().copied().collect();
    keys.sort();
    println!("map keys = {keys:?}");
    let s: String = vec!["x", "y", "z"].into_iter().collect();
    println!("string = {s}");

    // 4. Peekable lookahead, from_fn and successors.
    let mut p = "12+34".chars().peekable();
    let mut number = String::new();
    while let Some(c) = p.next_if(|c| c.is_ascii_digit()) {
        number.push(c);
    }
    println!("peekable read number = {number}, next = {:?}", p.peek());
    let mut n = 0;
    let evens: Vec<_> = std::iter::from_fn(|| {
        n += 2;
        (n <= 8).then_some(n)
    })
    .collect();
    println!("from_fn = {evens:?}");
    println!(
        "successors = {:?}",
        std::iter::successors(Some(1u32), |x| x.checked_mul(10)).collect::<Vec<_>>()
    );

    // 5. Custom iterators.
    println!("countdown = {:?}", Countdown(4).collect::<Vec<_>>());
    println!(
        "countdown zip = {:?}",
        Countdown(3).zip(Countdown(5).skip(1)).collect::<Vec<_>>()
    );
    let pl = Playlist {
        songs: vec!["one".into(), "two".into()],
    };
    for song in &pl {
        print!("{song} ");
    }
    println!();

    // 6. Closures capture by the least power needed: &, &mut, or move.
    let mut count = 0;
    call_twice(|| count += 1); // FnMut: mutably borrows `count`
    println!("count = {count}");
    let owned = String::from("owned");
    println!("{}", call_once(move || owned + " and consumed")); // FnOnce: moves `owned`
    let add5 = make_adder(5);
    println!(
        "add5(1) = {}, boxed double(4) = {}",
        add5(1),
        make_boxed("double")(4)
    );

    // 7. A Vec of different closures needs Box<dyn Fn>.
    let ops: Vec<(&str, Box<dyn Fn(i32) -> i32>)> =
        vec![("inc", Box::new(|x| x + 1)), ("sq", Box::new(|x| x * x))];
    for (name, f) in &ops {
        print!("{name}(7)={} ", f(7));
    }
    println!();

    // 8. Disjoint closure captures (edition 2021+): the closure borrows only the field it uses.
    struct S {
        a: String,
        b: String,
    }
    let mut s = S {
        a: "a".into(),
        b: "b".into(),
    };
    let read_a = || s.a.len();
    s.b.push('!'); // fine: the closure only borrows `s.a`
    println!("read_a = {}, b = {}", read_a(), s.b);

    // 9. Short-circuiting consumers stop early, even on infinite iterators.
    let first_big = (1u64..).map(|x| x * x).find(|sq| *sq > 200);
    println!("first square > 200 = {first_big:?}");
}
