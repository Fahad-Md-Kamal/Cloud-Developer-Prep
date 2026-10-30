//! Must FAIL to compile: outside its own crate, a `#[non_exhaustive]` enum needs a wildcard arm.
//! Check: copy over `crates/shop-app/src/main.rs`, then `cargo build -p shop-app` (restore after).
use shop_domain::OrderError;

fn main() {
    let e = OrderError::BadQuantity(0);
    match e {
        OrderError::BadQuantity(n) => println!("bad {n}"),
        OrderError::OutOfStock { sku } => println!("out {sku}"),
        OrderError::Storage(m) => println!("storage {m}"),
    }
}
