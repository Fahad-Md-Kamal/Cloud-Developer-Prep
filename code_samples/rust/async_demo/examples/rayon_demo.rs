//! Data parallelism with rayon. Run: cargo run --release --example rayon_demo
use rayon::prelude::*;
use std::time::Instant;

fn is_prime(n: u32) -> bool {
    n >= 2 && (2..).take_while(|d| d * d <= n).all(|d| n % d != 0)
}

fn main() {
    let n = 3_000_000u32;
    let t = Instant::now();
    let seq = (0..n).filter(|&x| is_prime(x)).count();
    let seq_t = t.elapsed();
    let t = Instant::now();
    let par = (0..n).into_par_iter().filter(|&x| is_prime(x)).count();
    let par_t = t.elapsed();
    assert_eq!(seq, par);
    println!("primes below {n}: {seq}");
    println!("sequential {seq_t:?}, parallel {par_t:?} on {} threads", rayon::current_num_threads());

    // reduce / sum / collect keep order
    let squares: Vec<u64> = (1..=5u64).into_par_iter().map(|x| x * x).collect();
    println!("order preserved: {squares:?}");
    let total: u64 = squares.par_iter().sum();
    println!("par sum: {total}");

    // rayon::join and scope
    let (a, b) = rayon::join(|| (1..=10u32).sum::<u32>(), || (1..=5u32).product::<u32>());
    println!("join: {a} {b}");
}
