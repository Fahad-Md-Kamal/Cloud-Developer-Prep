//! A tiny single-threaded async executor, std only.
//! Run: cargo run --example async_executor
use std::cell::RefCell;
use std::collections::VecDeque;
use std::future::Future;
use std::pin::Pin;
use std::rc::Rc;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::task::{Context, Poll, Wake, Waker};
use std::thread;
use std::time::{Duration, Instant};

// ---------- 1. A hand-written future: counts down, waking itself each time ----------
struct Countdown(u32);

impl Future for Countdown {
    type Output = &'static str;
    fn poll(mut self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Self::Output> {
        if self.0 == 0 {
            Poll::Ready("liftoff")
        } else {
            println!("   Countdown::poll, {} left", self.0);
            self.0 -= 1;
            cx.waker().wake_by_ref(); // "poll me again"
            Poll::Pending
        }
    }
}

// ---------- 2. A timer future: a helper thread calls the waker ----------
struct Timer {
    shared: Arc<Mutex<TimerState>>,
}
struct TimerState {
    done: bool,
    waker: Option<Waker>,
}

impl Timer {
    fn new(d: Duration) -> Self {
        let shared = Arc::new(Mutex::new(TimerState {
            done: false,
            waker: None,
        }));
        let s2 = Arc::clone(&shared);
        thread::spawn(move || {
            thread::sleep(d);
            let mut st = s2.lock().unwrap();
            st.done = true;
            if let Some(w) = st.waker.take() {
                w.wake();
            }
        });
        Timer { shared }
    }
}

impl Future for Timer {
    type Output = ();
    fn poll(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<()> {
        let mut st = self.shared.lock().unwrap();
        if st.done {
            Poll::Ready(())
        } else {
            st.waker = Some(cx.waker().clone()); // always store the LATEST waker
            Poll::Pending
        }
    }
}

// ---------- 3. The executor ----------
type Task = Pin<Box<dyn Future<Output = ()>>>;

struct Flag {
    woken: Mutex<bool>,
    cv: std::sync::Condvar,
    wakes: AtomicUsize,
}
impl Wake for Flag {
    fn wake(self: Arc<Self>) {
        self.wakes.fetch_add(1, Ordering::Relaxed);
        *self.woken.lock().unwrap() = true;
        self.cv.notify_one();
    }
}

/// Run one future to completion on the current thread.
fn block_on<F: Future>(fut: F) -> (F::Output, usize) {
    let mut fut = std::pin::pin!(fut);
    let flag = Arc::new(Flag {
        woken: Mutex::new(false),
        cv: Default::default(),
        wakes: AtomicUsize::new(0),
    });
    let waker = Waker::from(Arc::clone(&flag));
    let mut cx = Context::from_waker(&waker);
    let mut polls = 0;
    loop {
        polls += 1;
        if let Poll::Ready(v) = fut.as_mut().poll(&mut cx) {
            return (v, polls);
        }
        // sleep until somebody wakes us
        let mut woken = flag.woken.lock().unwrap();
        while !*woken {
            woken = flag.cv.wait(woken).unwrap();
        }
        *woken = false;
    }
}

/// A multi-task round-robin executor (spawn several futures, poll them in turn).
struct Executor {
    queue: RefCell<VecDeque<Task>>,
}
impl Executor {
    fn spawn(&self, f: impl Future<Output = ()> + 'static) {
        self.queue.borrow_mut().push_back(Box::pin(f));
    }
    fn run(&self) {
        let waker = Waker::noop(); // busy polling: simple, fine for a demo
        let mut cx = Context::from_waker(waker);
        loop {
            let task = self.queue.borrow_mut().pop_front();
            let Some(mut task) = task else { break };
            if task.as_mut().poll(&mut cx).is_pending() {
                self.queue.borrow_mut().push_back(task);
            }
        }
    }
}

// ---------- 4. Yield once, to interleave tasks ----------
struct YieldNow(bool);
impl Future for YieldNow {
    type Output = ();
    fn poll(mut self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<()> {
        if self.0 {
            Poll::Ready(())
        } else {
            self.0 = true;
            cx.waker().wake_by_ref();
            Poll::Pending
        }
    }
}

async fn worker(name: &'static str, steps: u32, log: Rc<RefCell<Vec<String>>>) {
    for i in 1..=steps {
        log.borrow_mut().push(format!("{name}{i}"));
        YieldNow(false).await;
    }
}

async fn add_slowly(a: u32, b: u32) -> u32 {
    Timer::new(Duration::from_millis(30)).await;
    a + b
}

async fn big_buffer() -> usize {
    let buf = [0u8; 1024];
    YieldNow(false).await;
    buf.len() // `buf` lives across the await, so it is stored in the future
}

fn main() {
    println!("1. hand-written Countdown:");
    let (msg, polls) = block_on(Countdown(3));
    println!("   result = {msg}, polled {polls} times");

    println!("2. Timer + async fn (waker called from another thread):");
    let t = Instant::now();
    let (sum, polls) = block_on(async {
        let x = add_slowly(1, 2).await;
        add_slowly(x, 10).await
    });
    println!(
        "   sum = {sum}, polls = {polls}, elapsed >= 60ms: {}",
        t.elapsed() >= Duration::from_millis(60)
    );

    println!("3. futures are lazy:");
    let fut = async {
        println!("   (body running)");
        1
    };
    println!("   created the future, nothing printed yet");
    let (v, _) = block_on(fut);
    println!("   after block_on: {v}");

    println!("4. round-robin executor interleaves tasks:");
    let log = Rc::new(RefCell::new(Vec::new()));
    let ex = Executor {
        queue: RefCell::new(VecDeque::new()),
    };
    ex.spawn(worker("a", 3, Rc::clone(&log)));
    ex.spawn(worker("b", 3, Rc::clone(&log)));
    ex.run();
    println!("   order: {:?}", log.borrow());

    println!("5. future sizes (a future is a state machine value):");
    println!(
        "   size_of_val(async {{}})          = {}",
        size_of_val(&async {})
    );
    println!(
        "   size_of_val(big_buffer())       = {}",
        size_of_val(&big_buffer())
    );
    println!(
        "   size_of_val(add_slowly(1, 2))   = {}",
        size_of_val(&add_slowly(1, 2))
    );
    println!(
        "   size_of_val(Box::pin(big...))   = {}",
        size_of_val(&Box::pin(big_buffer()))
    );

    println!("6. cancellation by dropping:");
    struct Noisy;
    impl Drop for Noisy {
        fn drop(&mut self) {
            println!("   Noisy dropped (future cancelled mid-way)");
        }
    }
    let mut f = Box::pin(async {
        let _n = Noisy;
        YieldNow(false).await;
        println!("   never printed");
    });
    let mut cx = Context::from_waker(Waker::noop());
    let _ = f.as_mut().poll(&mut cx); // runs to the first await
    drop(f);

    println!("7. async closure (stable 1.85):");
    let double = async |x: u32| x * 2;
    println!("   {}", block_on(double(21)).0);
}
