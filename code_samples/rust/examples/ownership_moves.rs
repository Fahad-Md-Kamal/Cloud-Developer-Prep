//! Ownership: moves, Copy, clone, borrowing, drop order.
//! Run: cargo run --example ownership_moves

struct Noisy(&'static str);

impl Drop for Noisy {
    fn drop(&mut self) {
        println!("  drop {}", self.0);
    }
}

fn take(n: Noisy) {
    println!("  took {}", n.0);
} // `n` is dropped here, at the end of its scope

fn borrow(n: &Noisy) {
    println!("  borrowed {}", n.0);
}

struct Person {
    name: String,
    age: u32,
}

fn main() {
    println!("1. move into a function");
    let a = Noisy("a");
    take(a); // `a` is moved: using it after this line is a compile error
    println!("  after take");

    println!("2. Copy types are duplicated, not moved");
    let x = 5;
    let y = x;
    println!("  x={x} y={y}");

    println!("3. clone makes an explicit deep copy");
    let s = String::from("hi");
    let t = s.clone();
    println!("  s={s} t={t}");

    println!("4. borrowing does not move");
    let b = Noisy("b");
    borrow(&b);
    borrow(&b);
    println!("  still own b");

    println!("5. early drop and mem::take");
    let e = Noisy("e");
    drop(e);
    println!("  e is gone");
    let mut v = vec![1, 2, 3];
    let old = std::mem::take(&mut v);
    println!("  old={old:?} v={v:?}");

    println!("6. partial move out of a struct");
    let p = Person {
        name: "Ann".into(),
        age: 3,
    };
    let n = p.name; // moves only the `name` field
    println!("  name={n} age={}", p.age); // `age` is Copy and still usable

    println!("7. drop order is reverse declaration order");
    let _c = Noisy("c");
    let _d = Noisy("d");
    println!("end of main");
}
