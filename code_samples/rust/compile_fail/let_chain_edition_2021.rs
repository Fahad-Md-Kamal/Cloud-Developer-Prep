// Compile with: rustc --edition 2021 compile_fail/let_chain_edition_2021.rs
fn main() {
    let a = Some(5);
    if let Some(x) = a && x > 3 {
        println!("{x}");
    }
}
