//! Small utilities used to demonstrate testing in Rust.
//!
//! The crate is a library on purpose: `cargo test` runs unit tests, integration tests
//! (`tests/`) and the code examples inside these doc comments.

use std::fmt;
use std::time::Duration;

/// Turns a title into a URL-friendly slug.
///
/// # Examples
///
/// ```
/// use guru_samples::slugify;
/// assert_eq!(slugify("Hello, Rust World!"), "hello-rust-world");
/// ```
///
/// Repeated separators collapse, and edge separators are dropped:
///
/// ```
/// # use guru_samples::slugify;
/// assert_eq!(slugify("  --A  b-- "), "a-b");
/// ```
pub fn slugify(input: &str) -> String {
    let mut out = String::new();
    let mut pending_dash = false;
    for c in input.chars() {
        if c.is_alphanumeric() {
            if pending_dash && !out.is_empty() {
                out.push('-');
            }
            pending_dash = false;
            out.extend(c.to_lowercase());
        } else {
            pending_dash = true;
        }
    }
    out
}

/// Why a duration string could not be parsed.
#[derive(Debug, PartialEq, Eq)]
#[non_exhaustive]
pub enum ParseDurationError {
    /// The input was empty.
    Empty,
    /// The number part was not a valid unsigned integer.
    BadNumber(String),
    /// The unit was not one of `ms`, `s`, `m`, `h`.
    BadUnit(String),
}

impl fmt::Display for ParseDurationError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ParseDurationError::Empty => write!(f, "empty duration"),
            ParseDurationError::BadNumber(n) => write!(f, "bad number `{n}`"),
            ParseDurationError::BadUnit(u) => write!(f, "unknown unit `{u}`"),
        }
    }
}

impl std::error::Error for ParseDurationError {}

/// Parses strings such as `250ms`, `3s`, `2m` or `1h`.
///
/// ```
/// use std::time::Duration;
/// use guru_samples::parse_duration;
/// assert_eq!(parse_duration("2m"), Ok(Duration::from_secs(120)));
/// assert!(parse_duration("2x").is_err());
/// ```
pub fn parse_duration(s: &str) -> Result<Duration, ParseDurationError> {
    let s = s.trim();
    if s.is_empty() {
        return Err(ParseDurationError::Empty);
    }
    let split = s.find(|c: char| !c.is_ascii_digit()).unwrap_or(s.len());
    let (num, unit) = s.split_at(split);
    let n: u64 = num
        .parse()
        .map_err(|_| ParseDurationError::BadNumber(num.to_string()))?;
    match unit {
        "ms" => Ok(Duration::from_millis(n)),
        "s" => Ok(Duration::from_secs(n)),
        "m" => Ok(Duration::from_secs(n * 60)),
        "h" => Ok(Duration::from_secs(n * 3600)),
        other => Err(ParseDurationError::BadUnit(other.to_string())),
    }
}

/// A bounded stack that panics if you pop from an empty one (to demonstrate `should_panic`).
#[derive(Debug, Default)]
pub struct Stack<T> {
    items: Vec<T>,
}

impl<T> Stack<T> {
    pub fn new() -> Self {
        Stack { items: Vec::new() }
    }
    pub fn push(&mut self, item: T) {
        self.items.push(item);
    }
    /// # Panics
    ///
    /// Panics if the stack is empty.
    pub fn pop_or_panic(&mut self) -> T {
        self.items.pop().expect("pop from empty stack")
    }
    pub fn len(&self) -> usize {
        self.items.len()
    }
    pub fn is_empty(&self) -> bool {
        self.items.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;

    #[test]
    fn slugify_basic() {
        assert_eq!(slugify("Hello, World"), "hello-world");
    }

    #[test]
    fn slugify_handles_unicode() {
        assert_eq!(slugify("Crème Brûlée"), "crème-brûlée");
    }

    #[test]
    fn parse_each_unit() {
        assert_eq!(parse_duration("250ms").unwrap(), Duration::from_millis(250));
        assert_eq!(parse_duration("3s").unwrap(), Duration::from_secs(3));
        assert_eq!(parse_duration("1h").unwrap(), Duration::from_secs(3600));
    }

    // A test may return Result, so `?` works inside it.
    #[test]
    fn parse_with_question_mark() -> Result<(), ParseDurationError> {
        let d = parse_duration("10s")?;
        assert_eq!(d.as_secs(), 10);
        Ok(())
    }

    #[test]
    fn parse_errors_are_specific() {
        assert_eq!(parse_duration(""), Err(ParseDurationError::Empty));
        assert_eq!(
            parse_duration("5x"),
            Err(ParseDurationError::BadUnit("x".into()))
        );
        assert!(matches!(
            parse_duration("ms"),
            Err(ParseDurationError::BadNumber(_))
        ));
    }

    #[test]
    #[should_panic(expected = "pop from empty stack")]
    fn empty_pop_panics() {
        Stack::<i32>::new().pop_or_panic();
    }

    #[test]
    #[ignore = "slow: run with `cargo test -- --ignored`"]
    fn slow_test() {
        std::thread::sleep(Duration::from_millis(200));
    }

    proptest! {
        // Property: slugify is idempotent (slugifying a slug changes nothing).
        #[test]
        fn slugify_is_idempotent(s in ".{0,40}") {
            let once = slugify(&s);
            prop_assert_eq!(slugify(&once), once);
        }

        // Property: a formatted `{n}s` always parses back to n seconds.
        #[test]
        fn seconds_round_trip(n in 0u64..1_000_000) {
            prop_assert_eq!(parse_duration(&format!("{n}s")).unwrap().as_secs(), n);
        }
    }
}
