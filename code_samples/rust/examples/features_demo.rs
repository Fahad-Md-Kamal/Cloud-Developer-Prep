//! Cargo features: compile-time switches.
//! Run: cargo run --example features_demo
//! Run: cargo run --example features_demo --features fancy

fn main() {
    println!("base behaviour");
    #[cfg(feature = "fancy")]
    println!("the `fancy` feature is ON");
    #[cfg(not(feature = "fancy"))]
    println!("the `fancy` feature is OFF");

    if cfg!(debug_assertions) {
        println!("debug assertions are enabled (dev profile)");
    } else {
        println!("debug assertions are disabled (release profile)");
    }
}
