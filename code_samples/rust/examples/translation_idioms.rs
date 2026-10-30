//! Rust versions of everyday Python, Go and Kotlin idioms.
//! Run: cargo run --example translation_idioms

use std::collections::HashMap;
use std::fmt;
use std::sync::{Arc, Mutex, mpsc};
use std::thread;

// ---- Python: dataclass + dict + comprehension ------------------------------
#[derive(Debug, Clone, PartialEq)]
struct User {
    name: String,
    age: u8,
}

fn python_idioms() {
    println!("-- Python idioms");
    let users = [
        User {
            name: "ana".into(),
            age: 31,
        },
        User {
            name: "bo".into(),
            age: 17,
        },
        User {
            name: "cy".into(),
            age: 45,
        },
    ];
    // [u.name.upper() for u in users if u.age >= 18]
    let adults: Vec<String> = users
        .iter()
        .filter(|u| u.age >= 18)
        .map(|u| u.name.to_uppercase())
        .collect();
    println!("comprehension: {adults:?}");

    // {u.name: u.age for u in users}
    let by_name: HashMap<&str, u8> = users.iter().map(|u| (u.name.as_str(), u.age)).collect();
    println!("dict comprehension: bo is {}", by_name["bo"]);

    // collections.Counter / defaultdict(int)
    let mut counts: HashMap<char, usize> = HashMap::new();
    for c in "hello".chars() {
        *counts.entry(c).or_insert(0) += 1;
    }
    let mut pairs: Vec<_> = counts.into_iter().collect();
    pairs.sort();
    println!("Counter: {pairs:?}");

    // a, b = b, a ; enumerate ; zip
    let (mut a, mut b) = (1, 2);
    std::mem::swap(&mut a, &mut b);
    for (i, (x, y)) in ["a", "b"].iter().zip([10, 20]).enumerate() {
        println!("enumerate/zip: {i} {x} {y}");
    }
    println!("swap: {a} {b}");

    // d.get("k", default) / d.get("k") returning None
    println!(
        "dict.get: {:?} {}",
        by_name.get("zz"),
        by_name.get("zz").copied().unwrap_or(0)
    );
}

// ---- Go: (value, err) vs Result, sentinel errors, defer, goroutine + channel -
#[derive(Debug)]
enum ParseErr {
    Empty,
    Bad(std::num::ParseIntError),
}
impl fmt::Display for ParseErr {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ParseErr::Empty => write!(f, "empty input"),
            ParseErr::Bad(e) => write!(f, "bad number: {e}"),
        }
    }
}
impl std::error::Error for ParseErr {}
impl From<std::num::ParseIntError> for ParseErr {
    fn from(e: std::num::ParseIntError) -> Self {
        ParseErr::Bad(e)
    }
}

// Go: func parse(s string) (int, error) { if s == "" { return 0, ErrEmpty }; ... }
fn parse(s: &str) -> Result<i32, ParseErr> {
    if s.is_empty() {
        return Err(ParseErr::Empty);
    }
    Ok(s.parse::<i32>()?) // the `?` is Go's `if err != nil { return 0, err }`
}

struct Guard(&'static str);
impl Drop for Guard {
    fn drop(&mut self) {
        println!("defer-like cleanup: {}", self.0);
    }
}

fn go_idioms() {
    println!("-- Go idioms");
    for s in ["42", "", "x1"] {
        match parse(s) {
            Ok(n) => println!("parse({s:?}) = {n}"),
            Err(e) => println!("parse({s:?}) failed: {e}"),
        }
    }
    {
        let _g = Guard("closing the file"); // `defer file.Close()`: runs at scope end, in reverse order
        println!("working while the guard is alive");
    }

    // go func() { ch <- compute() }() ; v := <-ch
    let (tx, rx) = mpsc::channel();
    let handles: Vec<_> = (0..3)
        .map(|i| {
            let tx = tx.clone();
            thread::spawn(move || tx.send(i * i).unwrap())
        })
        .collect();
    drop(tx); // close the channel: without this the loop below never ends
    for h in handles {
        h.join().unwrap();
    }
    let mut got: Vec<i32> = rx.iter().collect();
    got.sort();
    println!("channel results: {got:?}");

    // var mu sync.Mutex; counter++  (Rust: the data lives INSIDE the mutex)
    let counter = Arc::new(Mutex::new(0));
    let hs: Vec<_> = (0..4)
        .map(|_| {
            let c = Arc::clone(&counter);
            thread::spawn(move || *c.lock().unwrap() += 1)
        })
        .collect();
    for h in hs {
        h.join().unwrap();
    }
    println!("mutex counter: {}", counter.lock().unwrap());
}

// ---- Kotlin: nullable types, ?., ?:, sealed class + when, extension fun ----
#[derive(Debug)]
enum Shape {
    Circle(f64),
    Rect { w: f64, h: f64 },
}

trait Describe {
    fn describe(&self) -> String;
}
// Kotlin: fun String.shout() = uppercase() + "!"  (extension function)
trait Shout {
    fn shout(&self) -> String;
}
impl Shout for str {
    fn shout(&self) -> String {
        self.to_uppercase() + "!"
    }
}
impl Describe for Shape {
    fn describe(&self) -> String {
        match self {
            Shape::Circle(r) => format!("circle {r}"),
            Shape::Rect { w, h } => format!("rect {w}x{h}"),
        }
    }
}

struct Person {
    nickname: Option<String>,
}

fn kotlin_idioms() {
    println!("-- Kotlin idioms");
    let p = Person { nickname: None };
    let q = Person {
        nickname: Some("zed".into()),
    };
    // p.nickname?.length ?: 0
    println!(
        "?. and ?: -> {} {}",
        p.nickname.as_deref().map_or(0, str::len),
        q.nickname.as_deref().map_or(0, str::len)
    );
    // val n = p.nickname!!  (throws) -> .unwrap() / .expect("..")
    println!("!! -> {}", q.nickname.as_ref().expect("nickname set"));
    // data class copy(...): struct update syntax
    let u = User {
        name: "ana".into(),
        age: 31,
    };
    let older = User {
        age: 32,
        ..u.clone()
    };
    println!("copy(age = 32): {older:?}");
    // when (shape) { is Circle -> ... }
    for s in [Shape::Circle(1.5), Shape::Rect { w: 2.0, h: 3.0 }] {
        println!("when: {}", s.describe());
    }
    println!("extension fun: {}", "hey".shout());
    // let / also / apply -> Option::map, a block, or Default + struct update
    println!("let: {:?}", Some(4).map(|n| n * 2));
}

fn main() {
    python_idioms();
    go_idioms();
    kotlin_idioms();
}
