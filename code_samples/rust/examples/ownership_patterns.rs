//! Ownership patterns that keep the borrow checker happy.
//! Run: cargo run --example ownership_patterns

use std::borrow::Cow;
use std::mem;

#[derive(Debug, Default)]
struct Job {
    name: String,
    retries: u32,
}

struct Queue {
    current: Option<Job>,
}

impl Queue {
    // take(): move the value OUT of a place that is behind &mut, leaving None behind.
    fn finish(&mut self) -> Option<Job> {
        self.current.take()
    }

    // mem::replace: swap in a new value, get the old one back.
    fn rename(&mut self, new_name: String) -> Option<String> {
        let job = self.current.as_mut()?;
        Some(mem::replace(&mut job.name, new_name))
    }
}

// Builder: methods take `self` by value, so calls chain and ownership flows through.
#[derive(Debug)]
struct Request {
    url: String,
    retries: u32,
}

struct RequestBuilder {
    url: String,
    retries: u32,
}

impl RequestBuilder {
    fn new(url: impl Into<String>) -> Self {
        RequestBuilder {
            url: url.into(),
            retries: 0,
        }
    }
    fn retries(mut self, n: u32) -> Self {
        self.retries = n;
        self
    }
    fn build(self) -> Request {
        Request {
            url: self.url,
            retries: self.retries,
        }
    }
}

// Cow: borrow when you can, allocate only when you must.
fn normalize(input: &str) -> Cow<'_, str> {
    if input.contains(' ') {
        Cow::Owned(input.replace(' ', "_")) // had to allocate
    } else {
        Cow::Borrowed(input) // zero-copy
    }
}

fn print_all(items: impl IntoIterator<Item = impl AsRef<str>>) {
    for i in items {
        print!("[{}]", i.as_ref());
    }
    println!();
}

fn main() {
    // Two-phase borrows: `v.push(v.len())` reads v while it is about to be mutated.
    let mut v = vec![1, 2, 3];
    v.push(v.len() as i32);
    println!("{v:?}");

    // `for x in v` MOVES v; `for x in &v` borrows it.
    let names = vec![String::from("a"), String::from("b")];
    for n in &names {
        print!("{n} ");
    }
    println!("(still usable: {})", names.len());
    for n in names {
        print!("{n} "); // owned Strings here
    }
    println!("(names was moved)");

    let mut q = Queue {
        current: Some(Job {
            name: "build".into(),
            retries: 0,
        }),
    };
    println!("renamed from {:?}", q.rename("deploy".into()));
    let done = q.finish();
    println!(
        "finished {done:?}, queue now {:?}",
        q.current.as_ref().map(|j| &j.name)
    );

    let req = RequestBuilder::new("https://example.com")
        .retries(3)
        .build();
    println!("{req:?}");
    println!("url={} retries={}", req.url, req.retries);

    let a = normalize("no_spaces");
    let b = normalize("has some spaces");
    println!(
        "{a} borrowed={} | {b} borrowed={}",
        matches!(a, Cow::Borrowed(_)),
        matches!(b, Cow::Borrowed(_))
    );

    print_all(["x", "y"]);
    print_all(vec![String::from("p"), String::from("q")]);

    // Index instead of holding a reference while mutating.
    let mut scores = vec![10, 20, 30];
    let best = (0..scores.len()).max_by_key(|&i| scores[i]).unwrap();
    scores[best] += 1;
    println!("{scores:?}");

    // Default::default + mem::take: leave a valid empty value behind.
    let mut job = Job {
        name: "x".into(),
        retries: 2,
    };
    let taken = mem::take(&mut job);
    println!("{taken:?} / {job:?} (retries was {})", taken.retries);
}
