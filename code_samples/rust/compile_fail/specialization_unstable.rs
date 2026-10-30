// Specialization is not stable.
trait Show {
    fn show(&self) -> String;
}

impl<T> Show for T {
    default fn show(&self) -> String {
        "something".to_string()
    }
}

impl Show for u8 {
    fn show(&self) -> String {
        "a byte".to_string()
    }
}

fn main() {
    println!("{}", 1u8.show());
}
