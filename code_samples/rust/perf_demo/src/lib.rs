//! Slow and fast versions of the same tasks, used by the performance page.

use std::collections::HashMap;

/// Slow: linear search in a Vec of (String, usize), String clone per word.
pub fn count_slow(words: &[String]) -> Vec<(String, usize)> {
    let mut counts: Vec<(String, usize)> = Vec::new();
    for w in words {
        let key = w.clone();
        match counts.iter_mut().find(|(k, _)| *k == key) {
            Some((_, n)) => *n += 1,
            None => counts.push((key, 1)),
        }
    }
    counts.sort();
    counts
}

/// Fast: HashMap keyed by `&str` (no clones), sorted once at the end.
pub fn count_fast(words: &[String]) -> Vec<(&str, usize)> {
    let mut counts: HashMap<&str, usize> = HashMap::with_capacity(1024);
    for w in words {
        *counts.entry(w.as_str()).or_insert(0) += 1;
    }
    let mut v: Vec<_> = counts.into_iter().collect();
    v.sort_unstable();
    v
}

pub fn sum_index(v: &[u64], idx: &[usize]) -> u64 {
    let mut s = 0;
    for &i in idx {
        s += v[i];
    }
    s
}

pub fn sum_loop(v: &[u64]) -> u64 {
    let mut s = 0;
    for i in 0..v.len() {
        s += v[i];
    }
    s
}

pub fn sum_iter(v: &[u64]) -> u64 {
    v.iter().sum()
}

pub fn make_words(n: usize, distinct: usize) -> Vec<String> {
    let mut x: u64 = 0x9E3779B97F4A7C15;
    (0..n)
        .map(|_| {
            x ^= x << 13;
            x ^= x >> 7;
            x ^= x << 17;
            format!("word{}", x as usize % distinct)
        })
        .collect()
}
