//! Types, enums and patterns, including let chains (2024) and if-let guards (1.95).
//! Run: cargo run --example types_and_patterns

#[derive(Debug)]
enum Shape {
    Circle { r: f64 },
    Rect { w: f64, h: f64 },
    Triangle(f64, f64, f64),
}

impl Shape {
    fn area(&self) -> f64 {
        match self {
            Shape::Circle { r } => std::f64::consts::PI * r * r,
            Shape::Rect { w, h } => w * h,
            Shape::Triangle(a, b, c) => {
                let s = (a + b + c) / 2.0;
                (s * (s - a) * (s - b) * (s - c)).sqrt()
            }
        }
    }
}

// Newtype: a distinct type with no runtime cost.
#[derive(Debug, Clone, Copy, PartialEq, PartialOrd)]
struct Meters(f64);

fn classify(n: i32) -> &'static str {
    match n {
        i32::MIN..=-1 => "negative",
        0 => "zero",
        x if x % 2 == 0 => "positive even",
        1 | 3 | 5 | 7 | 9 => "small odd",
        _ => "large odd",
    }
}

fn parse_kv(line: &str) -> Option<(&str, i32)> {
    // let-else: bind or diverge.
    let Some((k, v)) = line.split_once('=') else {
        return None;
    };
    let Ok(n) = v.trim().parse::<i32>() else {
        return None;
    };
    Some((k.trim(), n))
}

fn describe(items: &[i32]) -> String {
    // Slice patterns.
    match items {
        [] => "empty".into(),
        [x] => format!("one: {x}"),
        [first, .., last] => format!("many: {first}..{last}"),
    }
}

fn main() {
    let shapes = [
        Shape::Circle { r: 1.0 },
        Shape::Rect { w: 2.0, h: 3.0 },
        Shape::Triangle(3.0, 4.0, 5.0),
    ];
    for s in &shapes {
        println!("{s:?} area = {:.2}", s.area());
    }

    let (a, b) = (Meters(3.0), Meters(4.5));
    println!("{a:?} < {b:?} = {}", a < b);

    for n in [-5, 0, 4, 7, 11] {
        println!("{n} is {}", classify(n));
    }

    println!("{:?} {:?}", parse_kv("age = 42"), parse_kv("oops"));
    println!("{} | {} | {}", describe(&[]), describe(&[7]), describe(&[1, 2, 3]));

    // Binding with @ and nested patterns.
    let msg = Some(15);
    if let Some(n @ 10..=20) = msg {
        println!("in range: {n}");
    }

    // Let chains (stable in edition 2024 since Rust 1.88).
    let name: Option<&str> = Some("42");
    let limit: Option<i32> = Some(100);
    if let Some(s) = name
        && let Ok(n) = s.parse::<i32>()
        && let Some(max) = limit
        && n < max
    {
        println!("let chain ok: {n} < {max}");
    }

    // `if let` guards in match arms (stable since Rust 1.95).
    for input in [Some("7"), Some("x"), None] {
        let text = match input {
            Some(s) if let Ok(n) = s.parse::<i32>() => format!("number {n}"),
            Some(s) => format!("not a number: {s}"),
            None => "nothing".to_string(),
        };
        println!("{text}");
    }

    // matches! for a quick boolean test.
    println!("is circle: {}", matches!(shapes[0], Shape::Circle { r } if r > 0.5));
}
