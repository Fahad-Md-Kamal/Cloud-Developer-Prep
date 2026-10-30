//! A tiny program used to demonstrate the CI pipeline, the Docker build and the supply-chain tools.
fn main() {
    let v = serde_json::json!({ "app": "hello-ci", "ok": true });
    println!("{v}");
}
