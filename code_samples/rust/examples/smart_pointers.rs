//! Smart pointers: Box, Rc/Weak, RefCell/Cell, Arc, Cow, Deref, OnceLock/LazyLock.
//! Run: cargo run --example smart_pointers

use std::borrow::Cow;
use std::cell::{Cell, RefCell};
use std::ops::Deref;
use std::rc::{Rc, Weak};
use std::sync::{Arc, LazyLock, OnceLock};

// 1. Box: a heap allocation with one owner. Needed for recursive types.
#[derive(Debug)]
enum List {
    Cons(i32, Box<List>),
    Nil,
}
use List::{Cons, Nil};

fn sum(l: &List) -> i32 {
    match l {
        Cons(v, rest) => v + sum(rest),
        Nil => 0,
    }
}

// 2. A custom smart pointer: Deref gives `*p` and deref coercion; Drop gives cleanup.
struct MyBox<T: std::fmt::Debug>(T);
impl<T: std::fmt::Debug> Deref for MyBox<T> {
    type Target = T;
    fn deref(&self) -> &T {
        &self.0
    }
}
impl<T: std::fmt::Debug> Drop for MyBox<T> {
    fn drop(&mut self) {
        println!("  dropping MyBox({:?})", self.0);
    }
}
fn greet(name: &str) -> String {
    format!("hello {name}")
}

// 3. Rc + Weak: a tree where children own nothing upward (Weak avoids a reference cycle).
struct Node {
    name: String,
    parent: RefCell<Weak<Node>>,
    children: RefCell<Vec<Rc<Node>>>,
}
impl Drop for Node {
    fn drop(&mut self) {
        println!("  drop node {}", self.name);
    }
}

// 4. Global state without `static mut`.
static CONFIG: OnceLock<String> = OnceLock::new();
static TABLE: LazyLock<Vec<u32>> = LazyLock::new(|| {
    println!("  (computing TABLE once)");
    (1..=5).map(|x| x * x).collect()
});

fn main() {
    println!("1. Box");
    let l = Cons(1, Box::new(Cons(2, Box::new(Cons(3, Box::new(Nil))))));
    println!("  sum = {}, size_of Box<List> = {}", sum(&l), size_of::<Box<List>>());

    println!("2. Deref and Drop");
    {
        let b = MyBox(String::from("rust"));
        println!("  {} (deref coercion: &MyBox<String> -> &String -> &str)", greet(&b));
        println!("  len through Deref = {}", b.len());
    }

    println!("3. Rc, Weak and RefCell");
    let leaf = Rc::new(Node { name: "leaf".into(), parent: RefCell::new(Weak::new()), children: RefCell::new(vec![]) });
    println!("  leaf parent before = {:?}", leaf.parent.borrow().upgrade().map(|p| p.name.clone()));
    {
        let branch = Rc::new(Node { name: "branch".into(), parent: RefCell::new(Weak::new()), children: RefCell::new(vec![Rc::clone(&leaf)]) });
        *leaf.parent.borrow_mut() = Rc::downgrade(&branch);
        println!("  leaf parent now = {:?}", leaf.parent.borrow().upgrade().map(|p| p.name.clone()));
        println!("  branch strong={} weak={}", Rc::strong_count(&branch), Rc::weak_count(&branch));
        println!("  leaf   strong={} weak={}", Rc::strong_count(&leaf), Rc::weak_count(&leaf));
        println!("  branch has {} child(ren)", branch.children.borrow().len());
    } // branch dropped here: its strong count hit 0
    println!("  leaf parent after = {:?}", leaf.parent.borrow().upgrade().map(|p| p.name.clone()));

    println!("4. RefCell moves the borrow rules to run time");
    let cell = RefCell::new(vec![1, 2, 3]);
    {
        let r1 = cell.borrow();
        let r2 = cell.borrow(); // many shared borrows: fine
        println!("  two readers: {} {}", r1.len(), r2.len());
        println!("  try_borrow_mut while borrowed -> is_err = {}", cell.try_borrow_mut().is_err());
    }
    cell.borrow_mut().push(4);
    println!("  after push: {:?}", cell.borrow());
    let r = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        let _a = cell.borrow_mut();
        let _b = cell.borrow_mut(); // second mutable borrow: PANICS at run time
    }));
    println!("  double borrow_mut panicked = {}", r.is_err());

    println!("5. Cell for Copy values, no borrowing at all");
    let hits = Cell::new(0);
    let bump = || hits.set(hits.get() + 1);
    bump();
    bump();
    println!("  hits = {}", hits.get());

    println!("6. Rc::make_mut is copy-on-write");
    let mut a = Rc::new(vec![1, 2]);
    let b = Rc::clone(&a);
    Rc::make_mut(&mut a).push(3); // `a` was shared, so it clones the Vec first
    println!("  a={a:?} b={b:?} same_allocation={}", Rc::ptr_eq(&a, &b));

    println!("7. Arc is Rc that is safe to share between threads");
    let shared = Arc::new(String::from("shared"));
    let handles: Vec<_> = (0..3)
        .map(|i| {
            let s = Arc::clone(&shared);
            std::thread::spawn(move || format!("thread {i} sees {s}"))
        })
        .collect();
    for h in handles {
        println!("  {}", h.join().unwrap());
    }
    println!("  strong_count after joins = {}", Arc::strong_count(&shared));

    println!("8. Cow");
    let c1: Cow<str> = Cow::Borrowed("static text");
    let mut c2 = c1.clone();
    c2.to_mut().push_str(" + more"); // first write allocates
    println!("  {c1} | {c2} | c2 owned = {}", matches!(c2, Cow::Owned(_)));

    println!("9. OnceLock / LazyLock");
    CONFIG.set("production".into()).unwrap();
    println!("  config = {:?}, second set fails = {}", CONFIG.get(), CONFIG.set("x".into()).is_err());
    println!("  table = {:?}", *TABLE);
    println!("  table again = {:?}", TABLE.len());

    println!("10. Box::leak gives a &'static mut");
    let leaked: &'static mut String = Box::leak(Box::new(String::from("lives forever")));
    leaked.push('!');
    println!("  {leaked}");
    println!("end");
}
