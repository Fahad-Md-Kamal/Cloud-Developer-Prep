//! More advanced traits: return-position `impl Trait` in traits, `async fn` in traits,
//! const generics, associated consts, marker traits, supertraits, blanket impls,
//! `impl Trait for &T`, trait-object upcasting, and the "dyn-safe wrapper" pattern.
//! Run: cargo run --example advanced_traits_more

use std::fmt::{Debug, Display};

// 1. Return-position impl Trait in a trait (RPITIT): each impl picks its own concrete type.
trait Source {
    fn items(&self) -> impl Iterator<Item = u32>;
}
struct Evens(u32);
struct Listed(Vec<u32>);
impl Source for Evens {
    fn items(&self) -> impl Iterator<Item = u32> {
        (0..self.0).filter(|n| n % 2 == 0)
    }
}
impl Source for Listed {
    fn items(&self) -> impl Iterator<Item = u32> {
        self.0.iter().copied()
    }
}
fn total<S: Source>(s: &S) -> u32 {
    s.items().sum()
}

// 2. async fn in a trait (stable): works with generics, but the trait is not dyn compatible.
trait Fetch {
    async fn fetch(&self, id: u32) -> String;
}
struct Fake;
impl Fetch for Fake {
    async fn fetch(&self, id: u32) -> String {
        format!("item-{id}")
    }
}
async fn fetch_two<F: Fetch>(f: &F) -> (String, String) {
    (f.fetch(1).await, f.fetch(2).await)
}

// 3. Const generics: a value as a type parameter.
#[derive(Debug)]
struct Matrix<const R: usize, const C: usize>([[i32; C]; R]);
impl<const R: usize, const C: usize> Matrix<R, C> {
    fn transpose(&self) -> Matrix<C, R> {
        let mut out = [[0; R]; C];
        for r in 0..R {
            for c in 0..C {
                out[c][r] = self.0[r][c];
            }
        }
        Matrix(out)
    }
}

// 4. Associated constants and a marker trait.
trait Shape {
    const SIDES: u32;
    fn name(&self) -> String;
}
struct Triangle;
struct Square;
impl Shape for Triangle {
    const SIDES: u32 = 3;
    fn name(&self) -> String {
        "triangle".into()
    }
}
impl Shape for Square {
    const SIDES: u32 = 4;
    fn name(&self) -> String {
        "square".into()
    }
}
fn corners<S: Shape>(_: &S) -> u32 {
    S::SIDES
}
trait Plain: Copy + 'static {} // a marker trait: no methods, only a promise
impl Plain for u8 {}
impl Plain for f32 {}
fn bytes_of<T: Plain>(v: &T) -> usize {
    size_of_val(v)
}

// 5. Supertraits and a blanket impl.
trait Named {
    fn name(&self) -> String;
}
trait Greeter: Named {
    fn greet(&self) -> String {
        format!("Hello, {}!", self.name())
    }
}
impl<T: Display> Named for T {
    fn name(&self) -> String {
        self.to_string()
    }
}
impl<T: Display> Greeter for T {}

// 6. Trait object upcasting (stable since 1.86).
trait Animal: Debug {
    fn noise(&self) -> &'static str;
}
#[derive(Debug)]
struct Dog;
impl Animal for Dog {
    fn noise(&self) -> &'static str {
        "woof"
    }
}

// 7. The "dyn-safe wrapper": make a non-dyn trait usable as `dyn` via a second trait.
trait Plugin {
    fn run(&self, input: &str) -> String;
}
trait DynPlugin {
    fn run_dyn(&self, input: &str) -> String;
}
impl<T: Plugin> DynPlugin for T {
    fn run_dyn(&self, input: &str) -> String {
        self.run(input)
    }
}
struct Upper;
impl Plugin for Upper {
    fn run(&self, input: &str) -> String {
        input.to_uppercase()
    }
}

// 8. Higher-ranked bound on a trait: works for ANY lifetime the caller picks.
trait Parser {
    fn parse<'a>(&self, s: &'a str) -> &'a str;
}
struct FirstWord;
impl Parser for FirstWord {
    fn parse<'a>(&self, s: &'a str) -> &'a str {
        s.split_whitespace().next().unwrap_or("")
    }
}
fn run_on_two<P>(p: &P) -> (String, String)
where
    P: for<'a> Fn(&'a str) -> &'a str,
{
    let a = String::from("alpha beta");
    let r1 = p(&a).to_string();
    let b = String::from("gamma delta");
    let r2 = p(&b).to_string();
    (r1, r2)
}

fn block_on<F: Future>(f: F) -> F::Output {
    use std::pin::pin;
    use std::task::{Context, Poll, Waker};
    let mut f = pin!(f);
    let mut cx = Context::from_waker(Waker::noop());
    loop {
        if let Poll::Ready(v) = f.as_mut().poll(&mut cx) {
            return v;
        }
    }
}

fn main() {
    println!(
        "RPITIT: evens {} listed {}",
        total(&Evens(10)),
        total(&Listed(vec![1, 2, 3]))
    );
    println!("async fn in trait: {:?}", block_on(fetch_two(&Fake)));
    let m = Matrix([[1, 2, 3], [4, 5, 6]]);
    println!("transpose of 2x3 = {:?}", m.transpose());
    println!(
        "consts: {} has {} sides, {} has {}",
        Triangle.name(),
        corners(&Triangle),
        Square.name(),
        corners(&Square)
    );
    println!(
        "marker: u8 {} bytes, f32 {} bytes",
        bytes_of(&1u8),
        bytes_of(&1.0f32)
    );
    println!("{} {}", 42.greet(), "Ferris".greet());
    let a: Box<dyn Animal> = Box::new(Dog);
    let d: Box<dyn Debug> = a; // upcast: dyn Animal -> dyn Debug
    println!("upcast: {d:?}, noise {}", Dog.noise());
    let plugins: Vec<Box<dyn DynPlugin>> = vec![Box::new(Upper)];
    println!("dyn wrapper: {}", plugins[0].run_dyn("abc"));
    println!("HRTB closure: {:?}", run_on_two(&|s| FirstWord.parse(s)));
}
