//! Advanced traits: typestate, sealed traits, GATs (lending iterator), extension traits,
//! PhantomData units, `dyn Any`, and associated consts.
//! Run: cargo run --example advanced_traits

use std::any::Any;
use std::fmt::Debug;
use std::marker::PhantomData;

// 1. Typestate: the state is a TYPE, so wrong-order calls do not compile.
struct Open;
struct Closed;

struct Door<State> {
    opened_times: u32,
    _state: PhantomData<State>,
}

impl Door<Closed> {
    fn new() -> Self {
        Door { opened_times: 0, _state: PhantomData }
    }
    fn open(self) -> Door<Open> {
        Door { opened_times: self.opened_times + 1, _state: PhantomData }
    }
}
impl Door<Open> {
    fn close(self) -> Door<Closed> {
        Door { opened_times: self.opened_times, _state: PhantomData }
    }
}
impl<S> Door<S> {
    fn times(&self) -> u32 {
        self.opened_times
    }
}

// 2. Sealed trait: public to use, impossible to implement outside this crate.
mod sealed {
    pub trait Sealed {}
}
trait Currency: sealed::Sealed {
    const CODE: &'static str;
}
struct Usd;
struct Eur;
impl sealed::Sealed for Usd {}
impl sealed::Sealed for Eur {}
impl Currency for Usd {
    const CODE: &'static str = "USD";
}
impl Currency for Eur {
    const CODE: &'static str = "EUR";
}

// 3. PhantomData as a unit marker: no run-time cost, no mixing currencies.
struct Money<C: Currency> {
    cents: i64,
    _c: PhantomData<C>,
}
impl<C: Currency> Money<C> {
    fn new(cents: i64) -> Self {
        Money { cents, _c: PhantomData }
    }
    fn add(&self, other: &Money<C>) -> Money<C> {
        Money::new(self.cents + other.cents)
    }
    fn show(&self) -> String {
        format!("{}.{:02} {}", self.cents / 100, self.cents % 100, C::CODE)
    }
}

// 4. A generic associated type (GAT): each item may BORROW from the iterator itself.
trait LendingIterator {
    type Item<'a>
    where
        Self: 'a;
    fn next<'a>(&'a mut self) -> Option<Self::Item<'a>>;
}

struct WindowsMut<'t, T> {
    slice: &'t mut [T],
    start: usize,
    size: usize,
}

impl<'t, T> LendingIterator for WindowsMut<'t, T> {
    type Item<'a>
        = &'a mut [T]
    where
        Self: 'a;
    fn next<'a>(&'a mut self) -> Option<&'a mut [T]> {
        let window = self.slice[self.start..].get_mut(..self.size)?;
        self.start += 1;
        Some(window)
    }
}

// 5. Extension trait: add methods to a type you do not own.
trait StrExt {
    fn is_palindrome(&self) -> bool;
}
impl StrExt for str {
    fn is_palindrome(&self) -> bool {
        let cs: Vec<char> = self.chars().filter(|c| c.is_alphanumeric()).collect();
        cs.iter().eq(cs.iter().rev())
    }
}

// 6. `dyn Any`: runtime type inspection for heterogeneous values.
fn describe(v: &dyn Any) -> String {
    if let Some(i) = v.downcast_ref::<i32>() {
        format!("i32 {i}")
    } else if let Some(s) = v.downcast_ref::<String>() {
        format!("String {s:?}")
    } else {
        "something else".to_string()
    }
}

// 7. A higher-ranked closure bound plus generic return.
fn apply_all<T: Debug, F>(items: &[T], f: F) -> Vec<String>
where
    F: for<'a> Fn(&'a T) -> String,
{
    items.iter().map(|i| f(i)).collect()
}

fn main() {
    let door = Door::new().open().close().open();
    println!("typestate door opened {} times", door.times());
    // Door::new().close();   // error: no method `close` for `Door<Closed>`

    let a: Money<Usd> = Money::new(1050);
    let b: Money<Usd> = Money::new(295);
    println!("{}", a.add(&b).show());
    let e: Money<Eur> = Money::new(100);
    println!("{} (a Money<Usd> cannot be added to this)", e.show());
    println!("size_of Money<Usd> = {} (same as i64)", size_of::<Money<Usd>>());

    let mut data = [1, 2, 3, 4, 5];
    let mut w = WindowsMut { slice: &mut data, start: 0, size: 3 };
    while let Some(win) = w.next() {
        win[0] += win[1] + win[2]; // overlapping windows, each mutable: impossible with Iterator
    }
    println!("lending iterator result = {data:?}");

    println!("{} {}", "A man, a plan, a canal: Panama".is_palindrome(), "rust".is_palindrome());

    let items: Vec<Box<dyn Any>> = vec![Box::new(5_i32), Box::new(String::from("hi")), Box::new(1.5_f64)];
    for it in &items {
        println!("{}", describe(it.as_ref()));
    }

    println!("{:?}", apply_all(&[1, 2, 3], |n| format!("<{n}>")));
}
