trait Fetch {
    async fn fetch(&self) -> u32;
}

struct A;
impl Fetch for A {
    async fn fetch(&self) -> u32 {
        1
    }
}

fn main() {
    let _x: Box<dyn Fetch> = Box::new(A);
}
