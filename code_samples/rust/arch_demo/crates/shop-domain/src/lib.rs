//! The core: types and rules plus the *ports* (traits) it needs from the outside.
//! This crate has no database, HTTP or file dependency.

use std::fmt;

/// A validated quantity. The field is private, so the only way to build one is `new`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Quantity(u32);

impl Quantity {
    pub fn new(n: u32) -> Result<Self, OrderError> {
        if n == 0 || n > 100 {
            Err(OrderError::BadQuantity(n))
        } else {
            Ok(Self(n))
        }
    }
    pub fn get(self) -> u32 {
        self.0
    }
}

impl fmt::Display for Quantity {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.0)
    }
}

/// `#[non_exhaustive]`: adding a variant later is NOT a breaking change,
/// because outside crates must already write a `_` arm.
#[derive(Debug, thiserror::Error, PartialEq)]
#[non_exhaustive]
pub enum OrderError {
    #[error("quantity {0} is not between 1 and 100")]
    BadQuantity(u32),
    #[error("out of stock: {sku}")]
    OutOfStock { sku: String },
    #[error("storage failed: {0}")]
    Storage(String),
}

#[derive(Debug, Clone, PartialEq)]
pub struct Order {
    pub sku: String,
    pub qty: Quantity,
}

/// Port: how the domain asks for stock. Adapters implement it.
pub trait Inventory {
    fn reserve(&mut self, sku: &str, qty: Quantity) -> Result<(), OrderError>;
}

/// Port: where finished orders go.
pub trait OrderLog {
    fn record(&mut self, order: &Order) -> Result<(), OrderError>;
}

/// The use case. Generic over the ports, so tests pass in-memory fakes.
pub fn place_order<I: Inventory, L: OrderLog>(
    inv: &mut I,
    log: &mut L,
    sku: &str,
    qty: u32,
) -> Result<Order, OrderError> {
    let qty = Quantity::new(qty)?;
    inv.reserve(sku, qty)?;
    let order = Order {
        sku: sku.to_owned(),
        qty,
    };
    log.record(&order)?;
    Ok(order)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;

    #[derive(Default)]
    struct FakeInv(HashMap<String, u32>);
    impl Inventory for FakeInv {
        fn reserve(&mut self, sku: &str, qty: Quantity) -> Result<(), OrderError> {
            match self.0.get_mut(sku) {
                Some(n) if *n >= qty.get() => {
                    *n -= qty.get();
                    Ok(())
                }
                _ => Err(OrderError::OutOfStock { sku: sku.into() }),
            }
        }
    }
    #[derive(Default)]
    struct FakeLog(Vec<Order>);
    impl OrderLog for FakeLog {
        fn record(&mut self, o: &Order) -> Result<(), OrderError> {
            self.0.push(o.clone());
            Ok(())
        }
    }

    #[test]
    fn happy_path_and_errors() {
        let mut inv = FakeInv::default();
        inv.0.insert("pen".into(), 5);
        let mut log = FakeLog::default();
        assert!(place_order(&mut inv, &mut log, "pen", 3).is_ok());
        assert_eq!(
            place_order(&mut inv, &mut log, "pen", 3),
            Err(OrderError::OutOfStock { sku: "pen".into() })
        );
        assert_eq!(
            place_order(&mut inv, &mut log, "pen", 0),
            Err(OrderError::BadQuantity(0))
        );
        assert_eq!(log.0.len(), 1);
    }
}
