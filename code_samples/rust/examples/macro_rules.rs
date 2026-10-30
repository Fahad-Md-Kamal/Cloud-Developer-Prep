//! Declarative macros: fragments, repetition, recursion, tt-muncher, internal rules, `$crate`, hygiene,
//! counting at compile time, and the edition 2024 `expr` / `expr_2021` fragment difference.
//! Run: cargo run --example macro_rules

use std::collections::HashMap;

// 1. Simple rule with fragment specifiers: $x:expr, $name:ident, $t:ty
macro_rules! square {
    ($x:expr) => {
        $x * $x
    };
}

// 2. Repetition: $( ... ),* with an optional trailing comma
macro_rules! hashmap {
    ($($k:expr => $v:expr),* $(,)?) => {{
        let mut m = HashMap::new();
        $( m.insert($k, $v); )*
        m
    }};
}

// 3. Recursion: max of any number of arguments
macro_rules! max {
    ($x:expr) => ($x);
    ($x:expr, $($rest:expr),+) => {{
        let a = $x;
        let b = max!($($rest),+);
        if a > b { a } else { b }
    }};
}

// 4. Generating items: a struct plus getters, from a list of fields
macro_rules! make_struct {
    ($name:ident { $($field:ident : $ty:ty),* $(,)? }) => {
        #[derive(Debug)]
        struct $name { $($field: $ty),* }
        impl $name {
            $( fn $field(&self) -> &$ty { &self.$field } )*
            fn field_names() -> &'static [&'static str] { &[$(stringify!($field)),*] }
        }
    };
}
make_struct!(Config {
    host: String,
    port: u16
});

// 5. Counting at compile time with recursion (no run-time cost)
macro_rules! count {
    () => (0usize);
    ($head:tt $($tail:tt)*) => (1usize + count!($($tail)*));
}

// 6. Internal rules (`@name`) and a tt-muncher: parse `key = value;` pairs one token group at a time
macro_rules! settings {
    (@acc $vec:ident;) => {};
    (@acc $vec:ident; $key:ident = $val:expr; $($rest:tt)*) => {
        $vec.push((stringify!($key), $val.to_string()));
        settings!(@acc $vec; $($rest)*);
    };
    ($($body:tt)*) => {{
        let mut v: Vec<(&str, String)> = Vec::new();
        settings!(@acc v; $($body)*);
        v
    }};
}

// 7. Hygiene: a local variable inside a macro does not clash with the caller's variable of the same name
macro_rules! double_it {
    ($e:expr) => {{
        let x = 2; // this `x` is invisible to the caller
        $e * x
    }};
}

// 8. `$crate`: always refer to your own crate's items by absolute path, so the macro works when exported
mod helpers {
    pub fn shout(s: &str) -> String {
        s.to_uppercase()
    }
}
macro_rules! shout_it {
    ($s:expr) => {
        $crate::helpers::shout($s)
    };
}

// 9. Edition 2024: `expr` now also matches `const { }` blocks and `_`; `expr_2021` keeps the old behaviour.
macro_rules! takes_expr {
    ($e:expr) => {
        "matched as expr"
    };
    ($($t:tt)*) => {
        "fell through to tt"
    };
}
macro_rules! takes_expr_2021 {
    ($e:expr_2021) => {
        "matched as expr_2021"
    };
    ($($t:tt)*) => {
        "fell through to tt"
    };
}

fn main() {
    println!(
        "square!(3 + 1) = {} (expr keeps precedence: (3+1)*(3+1))",
        square!(3 + 1)
    );

    let m = hashmap! { "a" => 1, "b" => 2, };
    let mut keys: Vec<_> = m.iter().collect();
    keys.sort();
    println!("hashmap! = {keys:?}");

    println!("max!(3, 9, 4) = {}", max!(3, 9, 4));

    let c = Config {
        host: "localhost".into(),
        port: 8080,
    };
    println!(
        "{:?} host()={} port()={} fields={:?}",
        c,
        c.host(),
        c.port(),
        Config::field_names()
    );

    const N: usize = count!(a b c d e);
    println!("count!(a b c d e) = {N}");

    println!(
        "settings! = {:?}",
        settings! { name = "demo"; retries = 3; debug = true; }
    );

    let x = 10;
    println!(
        "double_it!(x + 1) with caller x=10 -> {}",
        double_it!(x + 1)
    );

    println!("shout_it! = {}", shout_it!("hi"));

    println!("takes_expr!(const {{ 1 }}) -> {}", takes_expr!(const { 1 }));
    println!(
        "takes_expr_2021!(const {{ 1 }}) -> {}",
        takes_expr_2021!(const { 1 })
    );
    println!("takes_expr!(_) -> {}", takes_expr!(_));
}
