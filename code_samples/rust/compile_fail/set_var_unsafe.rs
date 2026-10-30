// Edition 2024: `std::env::set_var` is `unsafe` (it can race with other threads reading the environment).
fn main() {
    std::env::set_var("DEMO", "1");
}
