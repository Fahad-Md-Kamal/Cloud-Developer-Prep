//! Error-handling patterns: collecting results, transpose, try_fold, sizes, track_caller.
//! Run: cargo run --example error_patterns

use std::error::Error;
use std::num::ParseIntError;
use std::process::ExitCode;

fn parse_all(items: &[&str]) -> Result<Vec<i32>, ParseIntError> {
    // An iterator of Result<T, E> collects into Result<Vec<T>, E>: stops at the first Err.
    items.iter().map(|s| s.parse::<i32>()).collect()
}

fn sum_until_bad(items: &[&str]) -> Result<i32, ParseIntError> {
    items.iter().try_fold(0, |acc, s| Ok(acc + s.parse::<i32>()?))
}

fn maybe_number(s: Option<&str>) -> Result<Option<i32>, ParseIntError> {
    // Option<Result<T, E>> -> Result<Option<T>, E>
    s.map(|s| s.parse::<i32>()).transpose()
}

#[track_caller]
fn must_be_positive(n: i32) -> i32 {
    if n <= 0 {
        // The panic message points at the CALLER, not at this line.
        panic!("expected a positive number, got {n}");
    }
    n
}

#[derive(Debug)]
struct SmallError(#[allow(dead_code)] u8);
#[derive(Debug)]
struct BigError(#[allow(dead_code)] [u8; 256]);

fn run() -> Result<(), Box<dyn Error + Send + Sync>> {
    let v = parse_all(&["1", "2", "3"])?;
    println!("parsed {v:?}");
    let err = parse_all(&["1", "two", "3"]).unwrap_err();
    println!("collect stops at the first error: {err}");
    println!("try_fold ok = {:?}", sum_until_bad(&["4", "5"]));
    println!("try_fold bad = {:?}", sum_until_bad(&["4", "x"]).is_err());
    println!("transpose some = {:?}", maybe_number(Some("9")));
    println!("transpose none = {:?}", maybe_number(None));
    println!("transpose bad  = {:?}", maybe_number(Some("z")).is_err());

    println!("Result<(), SmallError> = {} bytes", size_of::<Result<(), SmallError>>());
    println!("Result<(), BigError>   = {} bytes", size_of::<Result<(), BigError>>());
    println!("Result<(), Box<BigError>> = {} bytes", size_of::<Result<(), Box<BigError>>>());

    let r = std::panic::catch_unwind(|| must_be_positive(-3));
    println!("track_caller panic caught = {}", r.is_err());

    // `?` converts any error into Box<dyn Error> using From.
    let n: i32 = "12x".parse()?;
    println!("never printed {n}");
    Ok(())
}

// `main` can return ExitCode to control the process exit status.
fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(e) => {
            println!("fatal: {e}");
            ExitCode::from(2)
        }
    }
}
