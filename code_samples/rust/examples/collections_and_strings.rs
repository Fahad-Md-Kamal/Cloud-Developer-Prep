//! Collections and strings: capacity, UTF-8, HashMap entry API, BTreeMap ranges, heaps.
//! Run: cargo run --example collections_and_strings

use std::cmp::Reverse;
use std::collections::{BTreeMap, BinaryHeap, HashMap, HashSet, VecDeque};

fn main() {
    // 1. Vec grows geometrically; `with_capacity` avoids reallocations.
    let mut v = Vec::new();
    let mut last_cap = v.capacity();
    for i in 0..40 {
        v.push(i);
        if v.capacity() != last_cap {
            println!("len {:>2} -> capacity {}", v.len(), v.capacity());
            last_cap = v.capacity();
        }
    }
    let mut w: Vec<u8> = Vec::with_capacity(1000);
    w.extend_from_slice(b"abc");
    println!("with_capacity: len={} cap>=1000? {}", w.len(), w.capacity() >= 1000);

    // 2. String is UTF-8 bytes. len() is bytes, not characters.
    let s = String::from("héllo 🦀");
    println!("bytes={} chars={}", s.len(), s.chars().count());
    for (i, c) in s.char_indices().filter(|(_, c)| !c.is_ascii()) {
        println!("  non-ascii {c:?} starts at byte {i} and is {} bytes", c.len_utf8());
    }
    println!("get(0..2) = {:?}", s.get(0..2)); // cuts inside 'é' -> None, no panic
    println!("get(0..3) = {:?}", s.get(0..3));
    println!("floor_char_boundary(2) = {}", s.floor_char_boundary(2)); // stable in 1.91

    // &str vs String: borrowed view vs owned buffer.
    fn shout(s: &str) -> String {
        s.to_uppercase()
    }
    println!("{}", shout(&s)); // &String coerces to &str

    // 3. HashMap entry API: one lookup for "insert or update".
    let text = "one two two three three three";
    let mut counts: HashMap<&str, usize> = HashMap::new();
    for word in text.split_whitespace() {
        *counts.entry(word).or_insert(0) += 1;
    }
    let mut pairs: Vec<_> = counts.iter().collect();
    pairs.sort_by(|a, b| b.1.cmp(a.1).then(a.0.cmp(b.0)));
    println!("{pairs:?}");

    // 4. BTreeMap keeps keys sorted and supports range queries.
    let mut scores = BTreeMap::new();
    for (name, pts) in [("ann", 70), ("bob", 85), ("cy", 92), ("di", 60)] {
        scores.insert(pts, name);
    }
    let top: Vec<_> = scores.range(80..).map(|(p, n)| (*n, *p)).collect();
    println!("scored 80+: {top:?}");
    println!("first={:?} last={:?}", scores.first_key_value(), scores.last_key_value());

    // 5. VecDeque: O(1) at both ends. BinaryHeap: a max-heap (use Reverse for a min-heap).
    let mut dq: VecDeque<i32> = (1..=3).collect();
    dq.push_front(0);
    dq.push_back(4);
    println!("{dq:?}");
    println!("pop_front = {:?}, then {dq:?}", dq.pop_front());
    let mut heap = BinaryHeap::new();
    for x in [5, 1, 8, 3] {
        heap.push(Reverse(x));
    }
    let order: Vec<_> = std::iter::from_fn(|| heap.pop().map(|Reverse(x)| x)).collect();
    println!("min-heap order: {order:?}");

    // 6. HashSet operations and retain / extract_if.
    let a: HashSet<_> = [1, 2, 3, 4].into_iter().collect();
    let b: HashSet<_> = [3, 4, 5].into_iter().collect();
    let mut inter: Vec<_> = a.intersection(&b).copied().collect();
    inter.sort();
    println!("intersection = {inter:?}");

    let mut nums: Vec<i32> = (1..=10).collect();
    let evens: Vec<i32> = nums.extract_if(.., |n| *n % 2 == 0).collect(); // stable since 1.87
    println!("evens={evens:?} odds={nums:?}");
}
