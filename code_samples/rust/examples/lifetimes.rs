//! Lifetimes: elision, structs that borrow, 'static, and Rust 2024 return-position impl Trait.
//! Run: cargo run --example lifetimes

// 1. Explicit lifetime: the result lives no longer than BOTH inputs.
fn longest<'a>(a: &'a str, b: &'a str) -> &'a str {
    if a.len() >= b.len() { a } else { b }
}

// 2. Elision: with ONE input reference, the output gets the same lifetime.
fn first_word(s: &str) -> &str {
    s.split_whitespace().next().unwrap_or("")
}

// 3. A struct that borrows must name the lifetime of what it borrows.
struct Parser<'src> {
    rest: &'src str,
}

impl<'src> Parser<'src> {
    fn new(src: &'src str) -> Self {
        Parser { rest: src }
    }

    // The returned token borrows from the ORIGINAL source ('src),
    // not from `&mut self`, so it can outlive this call.
    fn next_token(&mut self) -> Option<&'src str> {
        let rest = self.rest.trim_start();
        if rest.is_empty() {
            return None;
        }
        let end = rest.find(char::is_whitespace).unwrap_or(rest.len());
        let (tok, tail) = rest.split_at(end);
        self.rest = tail;
        Some(tok)
    }
}

// 4. Rust 2024: return-position `impl Trait` captures ALL in-scope lifetimes by default.
fn evens(v: &[i32]) -> impl Iterator<Item = &i32> {
    v.iter().filter(|x| **x % 2 == 0)
}

// 5. Opt out of capturing with `use<>` when the result must not borrow the input.
fn count_up(_label: &str, n: u32) -> impl Iterator<Item = u32> + use<> {
    0..n
}

// 6. `'static` as a TYPE bound means "contains no short-lived borrows", not "lives forever".
fn needs_static<T: 'static>(t: T) -> T {
    t
}

// 7. Higher-ranked bound: the closure must work for ANY lifetime of its argument.
fn apply_to_local<F>(f: F) -> usize
where
    F: for<'x> Fn(&'x str) -> &'x str,
{
    let local = String::from("local value");
    f(&local).len()
}

fn main() {
    let a = String::from("short");
    let result;
    {
        let b = String::from("longer one");
        result = longest(&a, &b).to_string(); // copy out before `b` dies
    }
    println!("longest = {result}");
    println!("first word = {}", first_word("hello brave world"));

    let text = String::from("let x = 42");
    let mut p = Parser::new(&text);
    let t1 = p.next_token();
    let t2 = p.next_token(); // t1 is still valid: it borrows `text`, not `p`
    println!("tokens: {t1:?} {t2:?}");

    let data = [1, 2, 3, 4, 5, 6];
    let e: Vec<_> = evens(&data).collect();
    println!("evens = {e:?}");

    let it = {
        let tmp = String::from("temp label");
        count_up(&tmp, 3) // fine only because of `use<>`
    };
    println!("count_up = {:?}", it.collect::<Vec<_>>());

    let owned: String = needs_static(String::from("owned data is 'static"));
    let literal: &'static str = needs_static("string literals are 'static");
    println!("{owned} / {literal}");

    println!("hrtb len = {}", apply_to_local(|s| s.trim()));
}
