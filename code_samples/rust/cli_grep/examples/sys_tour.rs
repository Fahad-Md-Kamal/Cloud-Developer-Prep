//! Systems tour: Command, File::lock, memory map, environment, Ctrl-C.
//! Run: `cargo run --example sys_tour`

use std::fs::{self, File, OpenOptions, TryLockError};
use std::io::Write;
use std::process::{Command, Stdio};
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};

fn main() -> anyhow::Result<()> {
    // 1. Run a child process and capture its output. No shell is involved: args are not re-parsed.
    let out = Command::new("echo")
        .args(["hello", "$HOME", "a b"])
        .output()?;
    println!(
        "echo -> {:?} status={}",
        String::from_utf8_lossy(&out.stdout),
        out.status
    );

    // 2. A pipeline by hand: child1 | child2
    let mut c1 = Command::new("printf")
        .arg("b\\na\\nc\\n")
        .stdout(Stdio::piped())
        .spawn()?;
    let sorted = Command::new("sort")
        .stdin(c1.stdout.take().unwrap())
        .output()?;
    c1.wait()?;
    println!("sorted -> {:?}", String::from_utf8_lossy(&sorted.stdout));

    // 3. A failing command: the exit status is data, not an error. Only spawn failure is an Err.
    let st = Command::new("false").status()?;
    println!("false -> success={} code={:?}", st.success(), st.code());
    println!(
        "missing -> {}",
        Command::new("no-such-program-xyz").status().unwrap_err()
    );

    // 4. Advisory file locks (std since 1.89). A second handle cannot lock exclusively.
    let path = std::env::temp_dir().join("rust_sys_tour.txt");
    let mut a = OpenOptions::new()
        .create(true)
        .write(true)
        .truncate(true)
        .open(&path)?;
    a.lock()?; // blocks until acquired
    writeln!(a, "line one\nline two\nneedle here")?;
    a.flush()?;
    let b = File::open(&path)?;
    match b.try_lock() {
        Err(TryLockError::WouldBlock) => println!("second handle: WouldBlock"),
        other => println!("unexpected: {other:?}"),
    }
    a.unlock()?;
    println!("after unlock, try_lock ok: {}", b.try_lock().is_ok());

    // 5. Memory-mapped file: treat the file as a byte slice. `unsafe` because another
    //    process could truncate or change the file while we read it.
    let map = unsafe { memmap2::Mmap::map(&File::open(&path)?)? };
    let pos = map.windows(6).position(|w| w == b"needle");
    println!("mmap: {} bytes, 'needle' at byte {:?}", map.len(), pos);
    drop(map);
    fs::remove_file(&path)?;

    // 6. Environment.
    println!(
        "PATH set: {}  MISSING: {:?}",
        std::env::var_os("PATH").is_some(),
        std::env::var("NOPE_X")
    );

    // 7. Ctrl-C handling: set a flag, let the main loop finish cleanly.
    let stop = Arc::new(AtomicBool::new(false));
    let s2 = stop.clone();
    ctrlc::set_handler(move || s2.store(true, Ordering::SeqCst))?;
    #[cfg(unix)]
    {
        // Send ourselves SIGINT to prove the handler runs.
        Command::new("kill")
            .args(["-INT", &std::process::id().to_string()])
            .status()?;
    }
    while !stop.load(Ordering::SeqCst) {
        std::thread::sleep(std::time::Duration::from_millis(10));
    }
    println!("got Ctrl-C, shutting down cleanly");
    Ok(())
}
