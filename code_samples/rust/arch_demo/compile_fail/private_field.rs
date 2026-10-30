//! Must FAIL to compile: `Quantity`'s field is private, so validation cannot be bypassed.
use shop_domain::Quantity;

fn main() {
    let _q = Quantity(0);
}
