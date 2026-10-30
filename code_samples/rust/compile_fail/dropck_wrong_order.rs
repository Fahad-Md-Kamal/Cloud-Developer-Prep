// Locals drop in reverse order. A value with a destructor must not outlive what it borrows.
struct Noisy<'a>(&'a str);
impl Drop for Noisy<'_> {
    fn drop(&mut self) {
        println!("dropping {}", self.0);
    }
}

fn main() {
    let n;
    let text = String::from("short-lived");
    n = Noisy(&text);
    let _ = &n;
}
