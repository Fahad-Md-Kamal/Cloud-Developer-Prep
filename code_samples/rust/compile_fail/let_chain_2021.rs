// Let chains need edition 2024. Compile with:
//   rustc --edition 2021 --emit=metadata -o /tmp/out compile_fail/let_chain_2021.rs
fn main() {
    let s = "12";
    if let Ok(n) = s.parse::<i32>()
        && n > 10
    {
        println!("{n}");
    }
}
