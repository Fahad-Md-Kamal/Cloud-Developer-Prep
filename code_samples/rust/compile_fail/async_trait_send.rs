// The future returned by an `async fn` in a trait is not known to be Send for a generic implementer.
trait Fetch { async fn fetch(&self) -> u32; }
fn spawnable<T: Fetch + Send + Sync + 'static>(t: T) {
    std::thread::spawn(move || {
        let _f = t.fetch();
        fn needs_send<X: Send>(_: X) {}
        needs_send(_f);
    });
}
fn main(){}
