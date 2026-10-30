//! Hand-rolled timing of common performance claims. Always run in release:
//!     cargo run --release --example bench_demo
//! Numbers depend on the machine; the page quotes the author's (aarch64 macOS).
use perf_demo::*;
use std::hint::black_box;
use std::time::Instant;

fn time<R>(label: &str, reps: u32, mut f: impl FnMut() -> R) -> f64 {
    black_box(f()); // warm up
    let t = Instant::now();
    for _ in 0..reps {
        black_box(f());
    }
    let per = t.elapsed().as_secs_f64() / reps as f64;
    println!("{label:<34} {:>10.1} us", per * 1e6);
    per
}

#[allow(dead_code)]
struct Particle { x: f32, y: f32, z: f32, vx: f32, vy: f32, vz: f32, mass: f32, id: u64, name: [u8; 32] }

fn main() {
    println!("-- push without and with capacity (1M u64)");
    let a = time("Vec::new + push", 20, || {
        let mut v = Vec::new();
        for i in 0..1_000_000u64 { v.push(i); }
        v
    });
    let b = time("Vec::with_capacity + push", 20, || {
        let mut v = Vec::with_capacity(1_000_000);
        for i in 0..1_000_000u64 { v.push(i); }
        v
    });
    println!("   ratio {:.2}x", a / b);

    println!("-- loop vs iterator (1M u64)");
    let data: Vec<u64> = (0..1_000_000).collect();
    time("index loop", 200, || sum_loop(black_box(&data)));
    time("iter().sum()", 200, || sum_iter(black_box(&data)));

    println!("-- array of structs vs struct of arrays (sum x, 100k)");
    let n = 100_000;
    let aos: Vec<Particle> = (0..n).map(|i| Particle { x: i as f32, y: 0., z: 0., vx: 0., vy: 0., vz: 0., mass: 1., id: i as u64, name: [0; 32] }).collect();
    let soa_x: Vec<f32> = aos.iter().map(|p| p.x).collect();
    println!("   size_of::<Particle>() = {} bytes", size_of::<Particle>());
    let a = time("AoS: sum p.x", 500, || aos.iter().map(|p| p.x).sum::<f32>());
    let b = time("SoA: sum x[]", 500, || soa_x.iter().sum::<f32>());
    println!("   ratio {:.2}x", a / b);

    println!("-- small lookup: Vec scan vs HashMap (8 keys)");
    let keys: Vec<(u32, u32)> = (0..8).map(|i| (i, i * 10)).collect();
    let map: std::collections::HashMap<u32, u32> = keys.iter().cloned().collect();
    time("Vec linear scan x1000", 2000, || { let mut s = 0; for q in 0..1000u32 { s += keys.iter().find(|(k, _)| *k == black_box(q % 8)).unwrap().1; } s });
    time("HashMap get x1000", 2000, || { let mut s = 0; for q in 0..1000u32 { s += map[&black_box(q % 8)]; } s });

    println!("-- worked example: count words (200k words, 500 distinct)");
    let words = make_words(200_000, 500);
    let slow = time("count_slow", 5, || count_slow(black_box(&words)));
    let fast = time("count_fast", 50, || count_fast(black_box(&words)));
    println!("   speed-up {:.0}x", slow / fast);
    assert_eq!(count_slow(&words).len(), count_fast(&words).len());
}
