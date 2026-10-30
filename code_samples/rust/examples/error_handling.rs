//! Error handling: Result, `?`, From, custom errors, thiserror, anyhow.
//! Run: cargo run --example error_handling

use std::error::Error;
use std::fmt;
use std::num::ParseIntError;

// 1. A hand-written error type: what thiserror generates for you.
#[derive(Debug)]
enum ConfigError {
    Missing(&'static str),
    BadNumber {
        key: &'static str,
        source: ParseIntError,
    },
}

impl fmt::Display for ConfigError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ConfigError::Missing(k) => write!(f, "missing key `{k}`"),
            ConfigError::BadNumber { key, .. } => write!(f, "key `{key}` is not a number"),
        }
    }
}

impl Error for ConfigError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            ConfigError::BadNumber { source, .. } => Some(source),
            _ => None,
        }
    }
}

fn port(cfg: &[(&str, &str)]) -> Result<u16, ConfigError> {
    let raw = cfg
        .iter()
        .find(|(k, _)| *k == "port")
        .map(|(_, v)| *v)
        .ok_or(ConfigError::Missing("port"))?; // `?` returns early on Err
    raw.parse::<u16>().map_err(|source| ConfigError::BadNumber {
        key: "port",
        source,
    })
}

// 2. The same idea with thiserror: less code, same behaviour.
#[derive(Debug, thiserror::Error)]
enum AppError {
    #[error("config problem: {0}")]
    Config(#[from] ConfigError), // `#[from]` also writes `impl From<ConfigError> for AppError`
    #[error("value {0} is out of range")]
    OutOfRange(u16),
}

fn checked_port(cfg: &[(&str, &str)]) -> Result<u16, AppError> {
    let p = port(cfg)?; // ConfigError is converted into AppError by `From`
    if p < 1024 {
        return Err(AppError::OutOfRange(p));
    }
    Ok(p)
}

// 3. anyhow for applications: any error, plus context.
fn run() -> anyhow::Result<()> {
    use anyhow::Context;
    let p = checked_port(&[("port", "80")]).context("while starting the server")?;
    println!("unreachable: {p}");
    Ok(())
}

fn print_chain(e: &dyn Error) {
    let mut cur: Option<&dyn Error> = Some(e);
    let mut depth = 0;
    while let Some(err) = cur {
        println!("{}{}", "  ".repeat(depth), err);
        cur = err.source();
        depth += 1;
    }
}

fn main() {
    println!("{:?}", port(&[("port", "8080")]));
    println!("{:?}", port(&[]));
    match port(&[("port", "eighty")]) {
        Err(e) => {
            println!("error chain:");
            print_chain(&e);
        }
        Ok(p) => println!("{p}"),
    }

    println!("{:?}", checked_port(&[("port", "80")]));

    if let Err(e) = run() {
        println!("anyhow chain:");
        for cause in e.chain() {
            println!("  - {cause}");
        }
    }

    // Useful small APIs.
    let opt: Option<u8> = None;
    println!("{:?}", opt.ok_or("no value"));
    let nested: Result<Result<u8, String>, String> = Ok(Err("inner".into()));
    println!("{:?}", nested.flatten()); // Result::flatten, stable since Rust 1.89

    // A panic is for bugs, not for expected failures.
    let r = std::panic::catch_unwind(|| {
        let v: Vec<i32> = Vec::new();
        v[0]
    });
    println!("panic caught: {}", r.is_err());
}
