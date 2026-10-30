//! Adapters: concrete implementations of the domain's ports.
//! A real project would have a Postgres adapter here; this one is in-memory and a file-less log.

use shop_domain::{Inventory, Order, OrderError, OrderLog, Quantity};
use std::collections::HashMap;

#[derive(Default)]
pub struct MemoryInventory(HashMap<String, u32>);

impl MemoryInventory {
    pub fn with_stock(items: &[(&str, u32)]) -> Self {
        Self(items.iter().map(|(s, n)| (s.to_string(), *n)).collect())
    }
}

impl Inventory for MemoryInventory {
    fn reserve(&mut self, sku: &str, qty: Quantity) -> Result<(), OrderError> {
        match self.0.get_mut(sku) {
            Some(n) if *n >= qty.get() => {
                *n -= qty.get();
                Ok(())
            }
            _ => Err(OrderError::OutOfStock {
                sku: sku.to_owned(),
            }),
        }
    }
}

#[derive(Default)]
pub struct StdoutLog;

impl OrderLog for StdoutLog {
    fn record(&mut self, o: &Order) -> Result<(), OrderError> {
        println!("recorded: {} x{}", o.sku, o.qty);
        Ok(())
    }
}
