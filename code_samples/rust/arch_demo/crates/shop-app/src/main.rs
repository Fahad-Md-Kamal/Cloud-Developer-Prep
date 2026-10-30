//! The composition root: the only place that knows which adapters are used.
//! Run from `code_samples/rust/arch_demo`: `cargo run -p shop-app`

use shop_adapters::{MemoryInventory, StdoutLog};
use shop_domain::{OrderError, place_order};

fn main() {
    let mut inv = MemoryInventory::with_stock(&[("pen", 5)]);
    let mut log = StdoutLog;
    for (sku, qty) in [("pen", 3), ("pen", 3), ("pen", 0)] {
        match place_order(&mut inv, &mut log, sku, qty) {
            Ok(o) => println!("ok: {o:?}"),
            // `OrderError` is #[non_exhaustive]: this crate MUST have a wildcard arm.
            Err(OrderError::OutOfStock { sku }) => println!("sorry, {sku} is out of stock"),
            Err(e) => println!("error: {e}"),
        }
    }
}
