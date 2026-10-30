//! Capstone 7: an interpreter for a tiny expression language.
//! Concepts: tokenizer, recursive-descent parser, `enum` AST with `Box`, `Result`, environments.
//! Grammar:  expr := term (('+'|'-') term)* ; term := factor (('*'|'/') factor)* ;
//!           factor := NUMBER | IDENT | '(' expr ')' | '-' factor

use std::collections::HashMap;

#[derive(Debug, PartialEq)]
pub enum EvalError {
    Syntax(String),
    UnknownVariable(String),
    DivisionByZero,
}

/// Evaluate `source` with the given variables.
pub fn eval(_source: &str, _vars: &HashMap<String, f64>) -> Result<f64, EvalError> {
    todo!("tokenize, parse into an AST, then walk it")
}

#[cfg(test)]
mod tests {
    use super::*;

    fn ev(s: &str) -> Result<f64, EvalError> {
        eval(s, &HashMap::from([("x".to_string(), 4.0)]))
    }

    #[test]
    #[ignore = "c07: implement eval"]
    fn c07_precedence_and_parens() {
        assert_eq!(ev("1 + 2 * 3"), Ok(7.0));
        assert_eq!(ev("(1 + 2) * 3"), Ok(9.0));
        assert_eq!(ev("-x + 10"), Ok(6.0));
    }

    #[test]
    #[ignore = "c07: implement eval"]
    fn c07_errors_are_values() {
        assert_eq!(ev("1 / 0"), Err(EvalError::DivisionByZero));
        assert_eq!(ev("y"), Err(EvalError::UnknownVariable("y".into())));
        assert!(matches!(ev("1 +"), Err(EvalError::Syntax(_))));
    }
}
