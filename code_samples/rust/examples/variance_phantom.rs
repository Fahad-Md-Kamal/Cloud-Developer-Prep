//! Variance, PhantomData and auto traits.
//! Run: cargo run --example variance_phantom

use std::cell::Cell;
use std::marker::PhantomData;

// 1. Covariance: a longer-lived reference can be used where a shorter one is expected.
fn shorten<'long: 'short, 'short>(x: &'long str) -> &'short str {
    x
}
fn covariant_demo() {
    let outer: &'static str = "static text";
    let r: &str = shorten(outer);
    println!("covariant: &'static str used as a shorter &str -> {r}");

    // Vec<&'a T> is covariant too.
    let v: Vec<&'static str> = vec!["a", "b"];
    let local = String::from("c");
    let mut shorter: Vec<&str> = v; // Vec<&'static str> -> Vec<&'short str>
    shorter.push(&local);
    println!("covariant: Vec<&'static str> coerced, then pushed a local: {shorter:?}");
}

// 2. Contravariance: fn(&'a T) accepts a function that handles ANY lifetime.
fn call_with_static(f: fn(&'static str) -> usize) -> usize {
    f("hello")
}
fn any_lifetime(s: &str) -> usize {
    s.len()
}

// 3. Variance of a custom struct is computed from its fields.
#[allow(dead_code)]
struct CovStruct<'a>(&'a str); // covariant in 'a
#[allow(dead_code)]
struct InvStruct<'a>(Cell<&'a str>); // invariant in 'a (Cell is invariant)
fn use_cov<'a>(_s: CovStruct<'a>) {}
fn cov_demo() {
    let s: CovStruct<'static> = CovStruct("x");
    let local = String::from("y");
    use_cov(s); // fine: CovStruct<'static> shrinks to the call's lifetime
    let _ = &local;
    println!("CovStruct shrinks freely; InvStruct would not");
    let _inv = InvStruct(Cell::new("z"));
}

// 4. PhantomData chooses variance and ownership for a type with raw pointers.
struct MyIter<'a, T> {
    ptr: *const T,
    left: usize,
    _marker: PhantomData<&'a T>, // "I hold a &'a T": covariant, no ownership
}
impl<'a, T> MyIter<'a, T> {
    fn new(slice: &'a [T]) -> Self {
        MyIter {
            ptr: slice.as_ptr(),
            left: slice.len(),
            _marker: PhantomData,
        }
    }
}
impl<'a, T> Iterator for MyIter<'a, T> {
    type Item = &'a T;
    fn next(&mut self) -> Option<&'a T> {
        if self.left == 0 {
            return None;
        }
        let item = unsafe { &*self.ptr };
        self.ptr = unsafe { self.ptr.add(1) };
        self.left -= 1;
        Some(item)
    }
}

// 5. PhantomData<fn() -> T>: be generic over T but own no T, keep Send/Sync independent of T.
struct Id<T> {
    raw: u64,
    _t: PhantomData<fn() -> T>,
}
impl<T> Clone for Id<T> {
    fn clone(&self) -> Self {
        *self
    }
}
impl<T> Copy for Id<T> {}
struct User;

// 6. Auto traits: Send / Sync are computed from fields; PhantomData can opt out.
struct NotSend(PhantomData<*const ()>);
#[allow(dead_code)]
struct RawHolder(*mut u8);
unsafe impl Send for RawHolder {} // a promise YOU make
fn assert_send<T: Send>() {}
fn assert_sync<T: Sync>() {}

// 7. Dropck: a type with Drop that borrows data forces that data to outlive it.
struct Noisy<'a>(&'a str);
impl Drop for Noisy<'_> {
    fn drop(&mut self) {
        println!("dropping Noisy({})", self.0);
    }
}

fn main() {
    covariant_demo();
    println!(
        "contravariant: fn(&str) used as fn(&'static str) -> {}",
        call_with_static(any_lifetime)
    );
    cov_demo();

    let data = [10, 20, 30];
    let sum: i32 = MyIter::new(&data).sum();
    println!("MyIter sum = {sum}");

    let a: Id<User> = Id {
        raw: 7,
        _t: PhantomData,
    };
    let b = a; // Copy even though User is not Copy
    println!("Id<User> copied: {} {}", a.raw, b.raw);

    assert_send::<i32>();
    assert_sync::<i32>();
    assert_send::<RawHolder>();
    assert_send::<Id<std::rc::Rc<u8>>>(); // fn() -> Rc<u8> is Send, so Id<Rc<u8>> is too
    println!(
        "Send/Sync checks passed; NotSend({}) is !Send (see compile_fail/phantom_not_send.rs)",
        size_of::<NotSend>()
    );

    let text = String::from("kept alive");
    let _n = Noisy(&text); // text declared BEFORE _n: dropped AFTER it
    println!("end of main");
}
