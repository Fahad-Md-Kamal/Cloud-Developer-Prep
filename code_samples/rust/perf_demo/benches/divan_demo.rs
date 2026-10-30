//! Run with: cargo bench   (inside code_samples/rust/perf_demo)
use perf_demo::*;

fn main() {
    divan::main();
}

#[divan::bench]
fn slow(bencher: divan::Bencher) {
    let words = make_words(20_000, 500);
    bencher.bench(|| count_slow(divan::black_box(&words)));
}

#[divan::bench]
fn fast(bencher: divan::Bencher) {
    let words = make_words(20_000, 500);
    bencher.bench(|| count_fast(divan::black_box(&words)));
}

#[divan::bench(args = [1_000, 100_000])]
fn sum_loop_bench(bencher: divan::Bencher, n: usize) {
    let v: Vec<u64> = (0..n as u64).collect();
    bencher.bench(|| sum_loop(divan::black_box(&v)));
}

#[divan::bench(args = [1_000, 100_000])]
fn sum_iter_bench(bencher: divan::Bencher, n: usize) {
    let v: Vec<u64> = (0..n as u64).collect();
    bencher.bench(|| sum_iter(divan::black_box(&v)));
}
