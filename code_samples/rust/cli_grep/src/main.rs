//! A small `grep`: `cargo run -- [-i] [-c] PATTERN [FILE...]`  (reads stdin when no FILE).
//! Exit codes follow grep: 0 = a match was found, 1 = no match, 2 = error.

use std::fs::File;
use std::io::{self, BufRead, BufReader, Write};
use std::process::ExitCode;

use anyhow::Context;
use clap::Parser;

#[derive(Parser, Debug)]
#[command(version, about = "Print lines that contain PATTERN")]
struct Args {
    /// Text to look for
    pattern: String,
    /// Files to search; standard input when empty
    files: Vec<std::path::PathBuf>,
    /// Ignore upper/lower case
    #[arg(short, long)]
    ignore_case: bool,
    /// Print only the number of matching lines per input
    #[arg(short, long)]
    count: bool,
}

fn search(
    args: &Args,
    name: &str,
    input: impl BufRead,
    out: &mut impl Write,
) -> anyhow::Result<usize> {
    let needle = if args.ignore_case {
        args.pattern.to_lowercase()
    } else {
        args.pattern.clone()
    };
    let mut hits = 0;
    for (i, line) in input.lines().enumerate() {
        let line = line.with_context(|| {
            format!(
                "{name}: line {} is not valid UTF-8 or could not be read",
                i + 1
            )
        })?;
        let hay = if args.ignore_case {
            line.to_lowercase()
        } else {
            line.clone()
        };
        if hay.contains(&needle) {
            hits += 1;
            if !args.count {
                writeln!(out, "{name}:{}:{line}", i + 1)?; // a broken pipe surfaces here as an Err
            }
        }
    }
    if args.count {
        writeln!(out, "{name}:{hits}")?;
    }
    Ok(hits)
}

fn run(args: &Args) -> anyhow::Result<bool> {
    let stdout = io::stdout();
    let mut out = io::BufWriter::new(stdout.lock());
    let mut total = 0;
    if args.files.is_empty() {
        total += search(args, "-", io::stdin().lock(), &mut out)?;
    }
    for path in &args.files {
        let f = File::open(path).with_context(|| format!("cannot open {}", path.display()))?;
        total += search(
            args,
            &path.display().to_string(),
            BufReader::new(f),
            &mut out,
        )?;
    }
    out.flush()?;
    Ok(total > 0)
}

fn main() -> ExitCode {
    match run(&Args::parse()) {
        Ok(true) => ExitCode::SUCCESS,
        Ok(false) => ExitCode::from(1),
        // `head` closed the pipe early: not an error worth printing (Rust ignores SIGPIPE).
        Err(e)
            if e.downcast_ref::<io::Error>()
                .is_some_and(|e| e.kind() == io::ErrorKind::BrokenPipe) =>
        {
            ExitCode::SUCCESS
        }
        Err(e) => {
            eprintln!("error: {e:#}");
            ExitCode::from(2)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn args(p: &str, ic: bool, count: bool) -> Args {
        Args {
            pattern: p.into(),
            files: vec![],
            ignore_case: ic,
            count,
        }
    }

    #[test]
    fn finds_lines() {
        let mut out = Vec::new();
        let n = search(
            &args("b", false, false),
            "t",
            "abc\nxyz\nB\nbb".as_bytes(),
            &mut out,
        )
        .unwrap();
        assert_eq!(n, 2);
        assert_eq!(String::from_utf8(out).unwrap(), "t:1:abc\nt:4:bb\n");
    }

    #[test]
    fn ignore_case_and_count() {
        let mut out = Vec::new();
        assert_eq!(
            search(
                &args("b", true, true),
                "t",
                "abc\nxyz\nB".as_bytes(),
                &mut out
            )
            .unwrap(),
            2
        );
        assert_eq!(String::from_utf8(out).unwrap(), "t:2\n");
    }
}
