//! Borrow rules and non-lexical lifetimes (NLL).
//! Run: cargo run --example borrow_rules

fn main() {
    // A shared borrow ends at its LAST USE, not at the end of the block.
    let mut v = vec![1, 2, 3];
    let first = &v[0];
    println!("first = {first}"); // last use of `first`
    v.push(4); // fine: the shared borrow is already over
    println!("{v:?}");

    // Many shared borrows OR exactly one mutable borrow, never both live at once.
    let r1 = &v;
    let r2 = &v;
    println!("{} {}", r1.len(), r2.len());
    let m = &mut v; // fine: r1 and r2 are no longer used
    m.push(5);
    println!("{v:?}");

    // Reborrowing: pass &mut without giving it away.
    fn add_one(x: &mut Vec<i32>) {
        x.push(1);
    }
    let m = &mut v;
    add_one(m);
    add_one(m); // `m` was reborrowed, not moved
    println!("{v:?}");

    // Splitting a borrow: disjoint fields can be borrowed mutably at once.
    struct Pair {
        a: i32,
        b: i32,
    }
    let mut p = Pair { a: 1, b: 2 };
    let ra = &mut p.a;
    let rb = &mut p.b;
    *ra += 10;
    *rb += 20;
    println!("{} {}", p.a, p.b);

    // Slices: split_at_mut gives two disjoint mutable halves.
    let mut arr = [1, 2, 3, 4];
    let (left, right) = arr.split_at_mut(2);
    left[0] = 100;
    right[0] = 300;
    println!("{arr:?}");
}
