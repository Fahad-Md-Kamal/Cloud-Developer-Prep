// Hygiene: a name the macro defines is invisible to the caller.
macro_rules! make_var {
    () => {
        let secret = 42;
    };
}

fn main() {
    make_var!();
    println!("{}", secret);
}
