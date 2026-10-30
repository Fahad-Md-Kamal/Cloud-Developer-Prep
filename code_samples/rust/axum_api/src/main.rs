//! Run: `cargo run` then `curl -s localhost:3000/notes`. Ctrl-C shuts down gracefully.

use axum_api::{AppState, app};
use tokio::{net::TcpListener, signal};

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt().init();
    let listener = TcpListener::bind("127.0.0.1:3000").await.unwrap();
    println!("listening on {}", listener.local_addr().unwrap());
    axum::serve(listener, app(AppState::default()))
        .with_graceful_shutdown(async {
            signal::ctrl_c().await.expect("install Ctrl-C handler");
            println!("shutting down: finishing in-flight requests");
        })
        .await
        .unwrap();
}
