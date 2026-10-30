//! Capstone 1: a `grep`-like search tool (library part).
//! Concepts: `&str` vs `String`, iterators, `Result`, `?`, lifetimes, tests.

use std::io::BufRead;

#[derive(Debug, PartialEq, Eq)]
pub struct Match {
    pub line_number: usize, // 1-based
    pub line: String,
}

#[derive(Debug, Default)]
pub struct Options {
    pub ignore_case: bool,
    pub invert: bool,
}

/// Return every line of `reader` that contains `pattern` (respecting `opts`).
pub fn search<R: BufRead>(
    _reader: R,
    _pattern: &str,
    _opts: &Options,
) -> std::io::Result<Vec<Match>> {
    todo!("read lines, filter, number them")
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Cursor;

    #[test]
    #[ignore = "c01: implement search"]
    fn c01_finds_lines_with_numbers() {
        let text = "alpha\nbeta\nalphabet\n";
        let got = search(Cursor::new(text), "alpha", &Options::default()).unwrap();
        assert_eq!(
            got.iter().map(|m| m.line_number).collect::<Vec<_>>(),
            [1, 3]
        );
    }

    #[test]
    #[ignore = "c01: implement search"]
    fn c01_ignore_case_and_invert() {
        let text = "Alpha\nbeta\n";
        let ci = Options {
            ignore_case: true,
            invert: false,
        };
        assert_eq!(search(Cursor::new(text), "alpha", &ci).unwrap().len(), 1);
        let inv = Options {
            ignore_case: false,
            invert: true,
        };
        assert_eq!(
            search(Cursor::new(text), "alpha", &inv).unwrap()[0].line,
            "Alpha"
        );
    }
}
