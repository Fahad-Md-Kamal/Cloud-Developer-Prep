// A `PhantomData<*const ()>` field makes the whole struct !Send (and !Sync).
use std::marker::PhantomData;

struct NotSend(PhantomData<*const ()>);

fn main() {
    let n = NotSend(PhantomData);
    std::thread::spawn(move || {
        let _n = n;
    });
}
