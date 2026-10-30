//! async fn in traits, the `Send` problem, a `dyn` workaround and AsyncFn bounds.
//! Run: cargo run --example async_traits
use std::future::Future;
use std::pin::Pin;
use std::task::{Context, Poll, Waker};

fn block_on<F: Future>(f: F) -> F::Output {
    let mut f = std::pin::pin!(f);
    let mut cx = Context::from_waker(Waker::noop());
    loop {
        if let Poll::Ready(v) = f.as_mut().poll(&mut cx) {
            return v;
        }
    }
}

// 1. async fn in a trait (stable since 1.75): fine with generics.
trait Fetch {
    async fn fetch(&self) -> u32;
}
struct A;
impl Fetch for A {
    async fn fetch(&self) -> u32 {
        1
    }
}
async fn use_generic<T: Fetch>(t: &T) -> u32 {
    t.fetch().await + 1
}

// 2. If callers need `Send`, say so in the trait with return-position impl Trait.
trait SendFetch {
    fn fetch(&self) -> impl Future<Output = u32> + Send;
}
impl SendFetch for A {
    async fn fetch(&self) -> u32 {
        2
    }
}
fn needs_send<F: Future + Send>(_f: F) {}

// 3. dyn workaround: return a boxed, pinned future by hand.
trait DynFetch {
    fn fetch(&self) -> Pin<Box<dyn Future<Output = u32> + '_>>;
}
impl DynFetch for A {
    fn fetch(&self) -> Pin<Box<dyn Future<Output = u32> + '_>> {
        Box::pin(async { 3 })
    }
}

// 4. AsyncFn bounds (stable 1.85): the closure may borrow from its argument.
async fn apply<F>(f: F, x: &str) -> usize
where
    F: AsyncFn(&str) -> usize,
{
    f(x).await
}

fn main() {
    println!(
        "1. generic async fn in trait: {}",
        block_on(use_generic(&A))
    );
    needs_send(SendFetch::fetch(&A));
    println!("2. Send-bounded trait method accepted by a Send-requiring function");
    let d: Box<dyn DynFetch> = Box::new(A);
    println!("3. dyn via boxed future: {}", block_on(d.fetch()));
    let n = block_on(apply(async |s| s.len(), "hello"));
    println!("4. AsyncFn bound with a borrowing closure: {n}");
}
