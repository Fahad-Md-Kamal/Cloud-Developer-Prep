// Trait aliases are not stable. The usual workaround is a trait with a blanket impl.
trait Both = Clone + std::fmt::Debug;

fn show<T: Both>(t: &T) {
    println!("{:?}", t.clone());
}

fn main() {
    show(&1);
}
