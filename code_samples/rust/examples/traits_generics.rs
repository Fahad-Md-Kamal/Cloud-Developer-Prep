//! Traits and generics: static vs dynamic dispatch, associated types, blanket impls,
//! const generics, supertraits and trait upcasting (stable since Rust 1.86).
//! Run: cargo run --example traits_generics

use std::fmt::{self, Debug, Display};
use std::ops::Add;

// 1. A trait with a required and a default method.
trait Describe {
    fn name(&self) -> String;
    fn describe(&self) -> String {
        format!("I am {}", self.name())
    }
}

struct Dog;
struct Robot(u32);

impl Describe for Dog {
    fn name(&self) -> String {
        "a dog".into()
    }
}
impl Describe for Robot {
    fn name(&self) -> String {
        format!("robot #{}", self.0)
    }
    fn describe(&self) -> String {
        format!("BEEP, {}", self.name()) // overrides the default
    }
}

// 2. Static dispatch: the compiler generates one copy per concrete type (monomorphization).
fn intro_static<T: Describe>(x: &T) -> String {
    format!(
        "[{}] {}",
        std::any::type_name::<T>().rsplit("::").next().unwrap(),
        x.describe()
    )
}

// 3. Dynamic dispatch: one copy of the code, a vtable lookup at run time.
fn intro_dyn(x: &dyn Describe) -> String {
    x.describe()
}

// 4. Associated type: the implementor picks ONE output type.
trait Container {
    type Item;
    fn first(&self) -> Option<&Self::Item>;
}
struct Stack<T>(Vec<T>);
impl<T> Container for Stack<T> {
    type Item = T;
    fn first(&self) -> Option<&T> {
        self.0.first()
    }
}
fn show_first<C: Container>(c: &C) -> String
where
    C::Item: Debug,
{
    format!("{:?}", c.first())
}

// 5. Blanket impl: implement a trait for EVERY type that meets a bound.
trait Shout {
    fn shout(&self) -> String;
}
impl<T: Display> Shout for T {
    fn shout(&self) -> String {
        self.to_string().to_uppercase() + "!"
    }
}

// 6. Operator overloading is just a trait.
#[derive(Debug, Clone, Copy, PartialEq)]
struct V2 {
    x: i32,
    y: i32,
}
impl Add for V2 {
    type Output = V2;
    fn add(self, o: V2) -> V2 {
        V2 {
            x: self.x + o.x,
            y: self.y + o.y,
        }
    }
}

// 7. Const generics: a value in the type.
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

// 8. Generic wrapper with a conditional impl.
struct Wrapper<T>(T);
impl<T: Display> Display for Wrapper<T> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "[{}]", self.0)
    }
}

// 9. Supertrait and trait upcasting.
trait Animal {
    fn legs(&self) -> u32;
}
trait Pet: Animal {
    fn owner(&self) -> &str;
}
struct Cat;
impl Animal for Cat {
    fn legs(&self) -> u32 {
        4
    }
}
impl Pet for Cat {
    fn owner(&self) -> &str {
        "Sam"
    }
}
fn count_legs(a: &dyn Animal) -> u32 {
    a.legs()
}

// 10. Trait with a generic method is NOT dyn compatible, but `where Self: Sized` opts it out.
trait Visitor {
    fn visit(&self, n: i32) -> i32;
    fn map_all<F: Fn(i32) -> i32>(&self, f: F) -> i32
    where
        Self: Sized,
    {
        f(self.visit(1))
    }
}
struct Doubler;
impl Visitor for Doubler {
    fn visit(&self, n: i32) -> i32 {
        n * 2
    }
}

fn largest<T: PartialOrd + Copy>(items: &[T]) -> T {
    let mut m = items[0];
    for &i in items {
        if i > m {
            m = i;
        }
    }
    m
}

fn main() {
    println!("{}", intro_static(&Dog));
    println!("{}", intro_static(&Robot(7)));

    let zoo: Vec<Box<dyn Describe>> = vec![Box::new(Dog), Box::new(Robot(9))];
    for z in &zoo {
        println!("dyn: {}", intro_dyn(z.as_ref()));
    }
    println!(
        "size_of &Dog = {}, size_of &dyn Describe = {}",
        size_of::<&Dog>(),
        size_of::<&dyn Describe>()
    );

    println!("first = {}", show_first(&Stack(vec![10, 20])));
    println!("{} {}", "hello".shout(), 42.shout());
    println!("{:?}", V2 { x: 1, y: 2 } + V2 { x: 10, y: 20 });
    println!("{:?}", Matrix([[1, 2, 3], [4, 5, 6]]).transpose());
    println!("{}", Wrapper(3.5));

    let cat = Cat;
    let pet: &dyn Pet = &cat;
    println!("owner={} legs={}", pet.owner(), count_legs(pet)); // upcast &dyn Pet -> &dyn Animal

    println!("{}", Doubler.map_all(|v| v + 100));
    let boxed: Box<dyn Visitor> = Box::new(Doubler);
    println!("dyn visit = {}", boxed.visit(21));

    println!(
        "{} {:.1} {}",
        largest(&[3, 9, 2]),
        largest(&[1.5, 0.2]),
        largest(&['x', 'b'])
    );
}
