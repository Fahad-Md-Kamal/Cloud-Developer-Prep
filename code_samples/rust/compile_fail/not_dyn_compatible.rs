trait Cloner {
    fn dup(&self) -> Self;
    fn map<F: Fn(i32) -> i32>(&self, f: F) -> i32;
}

fn use_it(_c: &dyn Cloner) {}

fn main() {}
