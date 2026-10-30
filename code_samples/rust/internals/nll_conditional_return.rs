//! Must FAIL on stable: the borrow checker (NLL) rejects a case Polonius accepts.
use std::collections::HashMap;

fn get_or_insert(map: &mut HashMap<u32, String>, k: u32) -> &String {
    if let Some(v) = map.get(&k) {
        return v;
    }
    map.insert(k, String::from("new"));
    &map[&k]
}

fn main() {
    let mut m = HashMap::new();
    println!("{}", get_or_insert(&mut m, 1));
}
