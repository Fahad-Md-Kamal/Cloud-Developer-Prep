// Edition 2024: the body of an `unsafe fn` is no longer an implicit unsafe block (lint warns).
unsafe fn read(p: *const i32) -> i32 {
    *p
}

fn main() {
    let x = 1;
    println!("{}", unsafe { read(&x) });
}
