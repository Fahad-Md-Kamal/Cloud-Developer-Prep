//! Edition 2024: temporaries in a block's tail expression are dropped BEFORE the locals.
//! Run: cargo run --example tail_expr_temporaries
//! Compile this file with `rustc --edition 2021` to see the old error.

use std::cell::RefCell;

fn len_of_cell() -> usize {
    let c = RefCell::new(String::from(".."));
    c.borrow().len() // the `Ref` temporary is dropped before `c` in edition 2024
}

fn main() {
    println!("{}", len_of_cell());
}
