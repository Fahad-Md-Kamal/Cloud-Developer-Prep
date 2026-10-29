// The drop checker: a type with a `Drop` impl may read its borrowed data during drop,
// so the borrowed data must outlive it.
struct Inspector<'a>(&'a u8);

impl<'a> Drop for Inspector<'a> {
    fn drop(&mut self) {
        println!("I was only {} days from retirement!", self.0);
    }
}

struct World<'a> {
    inspector: Option<Inspector<'a>>,
    days: Box<u8>,
}

fn main() {
    let mut world = World { inspector: None, days: Box::new(1) };
    world.inspector = Some(Inspector(&world.days));
}
