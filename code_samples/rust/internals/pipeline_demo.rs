//! Look at what rustc produces at each stage. See docs page "How rustc Works".
//!     rustc --edition 2024 -O --crate-type=lib --emit=mir,llvm-ir,asm pipeline_demo.rs
//! Count monomorphized copies:  rustc --edition 2024 -O -C codegen-units=1 pipeline_demo.rs && nm pipeline_demo | grep largest

#[inline(never)]
pub fn largest<T: PartialOrd + Copy>(xs: &[T]) -> T {
    let mut m = xs[0];
    for &x in xs {
        if x > m {
            m = x;
        }
    }
    m
}

pub const fn square(x: u32) -> u32 {
    x * x
}

const TABLE: [u32; 4] = [square(1), square(2), square(3), square(4)];

fn main() {
    println!("{}", largest(&[1_i32, 5, 3]));
    println!("{}", largest(&[1.5_f64, 0.5]));
    println!("{}", largest(&['a', 'z']));
    println!("{:?}", TABLE);
}
