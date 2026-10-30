use std::future::Future;

trait Fetch {
    async fn fetch(&self) -> u32;
}

fn needs_send<F: Future + Send>(_f: F) {}

fn generic<T: Fetch + Sync>(t: &T) {
    needs_send(t.fetch());
}

fn main() {}
