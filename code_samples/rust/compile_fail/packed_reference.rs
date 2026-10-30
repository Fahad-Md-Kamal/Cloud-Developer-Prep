// A reference to a field of a `repr(packed)` struct may be misaligned, which is undefined behaviour.
#[repr(C, packed)]
struct Packed {
    tag: u8,
    value: u32,
}

fn main() {
    let p = Packed { tag: 1, value: 7 };
    let r = &p.value;
    println!("{} {}", r, p.tag);
}
