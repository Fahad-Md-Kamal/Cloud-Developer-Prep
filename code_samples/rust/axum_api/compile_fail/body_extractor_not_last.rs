//! Must FAIL to compile: a body-consuming extractor (`Json`) must be the LAST argument.
//! Check: `cp compile_fail/body_extractor_not_last.rs examples/ && cargo build --example body_extractor_not_last`
use axum::{Json, Router, extract::State, routing::post};

async fn handler(Json(_body): Json<String>, State(_s): State<u32>) {}

fn main() {
    let _app: Router = Router::new().route("/", post(handler)).with_state(1u32);
}
