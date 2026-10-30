---
title: no_std and Embedded Rust — core vs alloc vs std, Panics, Allocators, and the Embedded HAL
---

# `no_std` and Embedded Rust

Normal Rust programs sit on an **operating system (OS)**: it provides
memory, files, threads, and a clock, and the standard library (`std`) is
built on those. A **`no_std`** program says "there may be no OS under me",
so it uses only the part of the library that needs nothing from outside.
That is how Rust runs on microcontrollers (a chip with a CPU and a few
kilobytes of memory), inside kernels and bootloaders, and in code that
must run anywhere.

!!! note "Version"
    Written for **Rust 1.99** and the **2024 edition**. The sample crate
    was built for the bare-metal target `thumbv7em-none-eabihf` (ARM
    Cortex-M4F) and tested on the host with 1.99.1. The three compiler
    errors quoted below are real output. **Not covered:** a complete
    flashed firmware. That needs a board, a linker script, and a debug
    probe, which this page describes but did not run.

## 1. "What are `core`, `alloc`, and `std`?"

**Answer:**

- The standard library is **three layers**, each built on the one before:

| Layer | Needs | Contains |
|---|---|---|
| **`core`** | nothing (no OS, no heap) | `Option`, `Result`, iterators, slices, `str`, `Cell`, atomics, `fmt` traits, `mem`, `ptr`, `hint`, `Duration`, math on integers |
| **`alloc`** | a **heap allocator** | `Box`, `Vec`, `String`, `Rc`, `Arc`, `BTreeMap`, `format!` |
| **`std`** | an **OS** | files, `println!`, threads, `Mutex`, `HashMap`, networking, `Instant`, `env` |

- `std` **re-exports** everything from `core` and `alloc`. `std::option::Option`
  and `core::option::Option` are the same type.
- `HashMap` is in `std`, not `alloc`, because its default hasher needs
  random numbers from the OS. In `no_std`, use `BTreeMap` (from `alloc`) or
  a crate such as `hashbrown` or `heapless`.
- Every ordinary crate links `std` automatically. Adding `#![no_std]` at
  the top of the crate root switches that off, and brings `core` into the
  prelude instead.

## 2. "What do you lose with `#![no_std]`?"

**Answer:**

- You lose **everything that needs an OS or a heap**. Real error for
  `Vec` and `println!` in a `#![no_std]` crate:

```text
error: cannot find macro `println` in this scope
 --> uses_std_in_no_std.rs:2:40
  |
2 | pub fn f() { let v = Vec::<u8>::new(); println!("{:?}", v); }
  |                                        ^^^^^^^

error[E0433]: cannot find type `Vec` in this scope
 --> uses_std_in_no_std.rs:2:22
  |
2 | pub fn f() { let v = Vec::<u8>::new(); println!("{:?}", v); }
  |                      ^^^ use of undeclared type `Vec`
```

- You **keep** all of the language: traits, generics, closures, pattern
  matching, iterators, `Option`/`Result`, the borrow checker, `const fn`.
  Rust's safety rules do not depend on the OS.
- You gain a few new concerns: **no heap** unless you add one, **no
  threads**, **no `println!`**, **no files**, and **you** decide what
  happens on `panic`.
- Fixed-size storage replaces growable storage. The sample's `Ring<T, N>`
  (a ring buffer) keeps its `N` slots **inline** with a **const generic**:

```rust
#![no_std]

pub struct Ring<T: Copy, const N: usize> {
    buf: [Option<T>; N],
    head: usize,
    len: usize,
}
// push returns Err(value) when full: nothing is allocated, nothing is dropped
```

- A test shows the cost is only the array: `size_of::<Ring<u8, 16>>()` equals
  `16 * 2 + 2 * size_of::<usize>()` (each `Option<u8>` is 2 bytes).

## 3. "What is `#![no_main]`, and why does a binary need a panic handler?"

**Answer:**

- A normal program starts in a function set up by `std` (it reads
  arguments, sets up the runtime, then calls your `main`). With no `std`
  there is **no runtime**, so `#![no_main]` tells the compiler not to expect
  one. **You** provide the real entry point: on a Cortex-M chip, a reset
  handler found through the **vector table** (a table of addresses at the
  start of flash memory). The `cortex-m-rt` crate sets this up.
- **A panic needs a handler.** In a `no_std` **binary** nobody says what a
  panic does, and the compiler refuses to build without an answer:

```rust
#![no_std]
#![no_main]

#[unsafe(no_mangle)]
pub extern "C" fn main() -> ! {
    loop {}
}
```

```text
error: `#[panic_handler]` function required, but not found
```

  (Built with `rustc --edition 2024 --target thumbv7em-none-eabihf -C panic=abort`.)

- The handler is a function that never returns:

```rust
#[panic_handler]
fn panic(_info: &core::panic::PanicInfo) -> ! {
    loop {} // or: reset the chip, blink an LED, write to a log
}
```

- Real projects use a crate that **is** a panic handler: `panic-halt`
  (stop), `panic-reset`, or `panic-probe` (send the message to the debug
  probe).
- **Libraries do not define a panic handler.** Only the final binary does,
  exactly once. Defining one in a library breaks users who want another.
- **Panics should abort.** The target spec for `thumbv7em-none-eabihf`
  already sets `panic="abort"` (shown by `rustc --print cfg --target ...`),
  so no unwinding tables are included. See
  [Performance Engineering §10](rust-performance-engineering.md#10-which-release-profile-settings-change-performance).

## 4. "How do you use `Vec` and `Box` without an OS?"

**Answer:**

- Add `extern crate alloc;` and **provide a global allocator**. Without one
  the compiler stops you. Real error (a `staticlib` with `alloc` but no
  allocator):

```text
error: no global memory allocator found but one is required; link to std or add `#[global_allocator]` to a static item that implements the GlobalAlloc trait
```

- A **global allocator** is a `static` of a type that implements
  `GlobalAlloc`, marked `#[global_allocator]`. On a microcontroller you
  hand it a region of RAM at start-up. Ready-made ones: `embedded-alloc`
  and `linked_list_allocator`.
- With the allocator in place, `Vec`, `String`, `Box`, `Rc`, and
  `BTreeMap` all work. The sample enables this with a Cargo **feature**,
  the standard pattern for libraries:

```toml
[features]
default = []
alloc = []
```

```rust
#[cfg(feature = "alloc")]
extern crate alloc;

#[cfg(feature = "alloc")]
pub fn drain_all<T: Copy, const N: usize>(r: &mut Ring<T, N>) -> alloc::vec::Vec<T> { /* ... */ }
```

- Both `cargo build --release --target thumbv7em-none-eabihf` and
  `... --features alloc` build for the bare target. Allocation **can fail**
  on small chips; the library builds its `Vec` only if the user asks.
- **Do you need a heap at all?** Often not. Many embedded programs avoid
  the heap on purpose: no fragmentation, no out-of-memory at run time, and
  the worst-case memory is known at build time. **`heapless`** provides
  `Vec`, `String`, `Deque`, and queues with a **fixed capacity** `N` that
  live on the stack or in a `static`.
- A related pattern for libraries on crates.io: compile as `no_std` unless
  a `std` feature is enabled, so the same crate serves both worlds:

```rust
#![cfg_attr(not(feature = "std"), no_std)]
```

  Dependencies then use `default-features = false` to avoid pulling `std`
  in by accident. A single dependency that needs `std` makes the whole
  build need it.

## 5. "How do you talk to hardware?"

**Answer:**

- On a microcontroller the peripherals (GPIO pins, timers, UART) are
  **memory-mapped registers**: reading or writing a fixed address
  controls the hardware.
- A normal read can be **removed or merged** by the optimizer, because
  to the compiler memory just holds values. **Volatile** access tells it
  "every read and write here is observable; do not skip or reorder them":

```rust
/// # Safety
/// `addr` must be a valid, aligned, readable register address.
pub unsafe fn read_reg(addr: *const u32) -> u32 {
    unsafe { core::ptr::read_volatile(addr) }
}
```

- This is `unsafe` because the compiler cannot check the address. Edition
  2024 also requires the inner `unsafe { }` block even inside an `unsafe fn`
  (the `unsafe_op_in_unsafe_fn` lint is on). See
  [Unsafe Rust & Miri](../advanced-language/rust-unsafe-and-miri.md).
- Since **1.90**, volatile access to memory that is **not Rust's** (such as
  device registers) is explicitly allowed by the language rules.
- You rarely write raw volatile code. Tools generate safe wrappers:
    - **PAC** (Peripheral Access Crate), generated by `svd2rust` from the
      chip vendor's SVD file (a description of all registers).
    - **HAL** (Hardware Abstraction Layer): a friendlier API over the PAC
      for one chip family (for example `stm32f4xx-hal`, `rp2040-hal`,
      `nrf52840-hal`).
    - **`embedded-hal`**: **traits** (`OutputPin`, `SpiBus`, `I2c`, `DelayNs`)
      that every HAL implements, so a sensor driver written once works on all
      chips.
- Rust's **ownership** helps here: a HAL hands out each peripheral **once**
  (`Peripherals::take()` returns `Some` the first time only), so "two
  parts of the code configure the same pin" is a compile or start-up error,
  not a runtime mystery. The **typestate** pattern (a pin of type
  `Pin<Output>` vs `Pin<Input>`) turns "wrote to an input pin" into a type
  error.

## 6. "How do you build and run on a target?"

**Answer:**

- A **target** is a triple `arch-vendor-os-abi`. `thumbv7em-none-eabihf`
  means: ARM Thumb-2, Cortex-M4F/M7, **no OS**, embedded ABI, **h**ardware
  **f**loating point. The compiler describes it (`rustc --print cfg`):

```text
panic="abort"       target_arch="arm"          target_pointer_width="32"
target_os="none"    target_has_atomic="32"     target_endian="little"
```

- Read it: **32-bit pointers**, **no OS**, panics abort, atomics up to
  32 bits (**no 64-bit atomics**), so code that assumes `AtomicU64` does not
  compile here.
- Steps (all run for the sample):

```bash
rustup target add thumbv7em-none-eabihf     # download the pre-built core and alloc
cargo build --release --target thumbv7em-none-eabihf
```

- The `rustup target add` step installs a **pre-built `core` and `alloc`**
  for the target. For targets without one, nightly can build them from
  source (`-Zbuild-std`).
- Choose a target by your chip:

| Chips | Target |
|---|---|
| Cortex-M0, M0+ | `thumbv6m-none-eabi` |
| Cortex-M3 | `thumbv7m-none-eabi` |
| Cortex-M4, M7 (no FPU) / (with FPU) | `thumbv7em-none-eabi` / `thumbv7em-none-eabihf` |
| Cortex-M33 | `thumbv8m.main-none-eabi` |
| RISC-V (for example ESP32-C3) | `riscv32imc-unknown-none-elf` |

- A real firmware crate also needs:
    - **A linker script** (`memory.x`) that says where flash and RAM are.
    - **`cortex-m-rt`**: start-up code, the vector table, the entry-point
      macro (`#[entry]`).
    - **`.cargo/config.toml`**: default target and a **runner**
      (`probe-rs run --chip ...`) so `cargo run` flashes the board.
- **`probe-rs`** is the standard open tool for flashing and debugging
  through a probe (a USB device wired to the chip's debug pins).
  **`defmt`** is a compact logging framework: the chip sends tiny numeric
  messages and the host expands them, which saves flash and time.

## 7. "What are Embassy and RTIC?"

**Answer:**

- A small chip still has to do **several things at once** (read a sensor,
  blink an LED, handle a button). Two Rust answers:
    - **Embassy**: **`async`/`await` on a microcontroller.** Tasks are
      futures, and one executor polls them; when all are waiting, the CPU
      sleeps. No heap and no OS needed. See
      [Async Internals](../concurrency-and-async/rust-async-internals.md).
    - **RTIC** (Real-Time Interrupt-driven Concurrency): tasks run in
      **interrupt handlers**, and resource sharing is checked at compile
      time with priorities, so there are no data races and no locks to
      forget.
- Compared with a **traditional RTOS** (FreeRTOS, Zephyr): in Rust the
  compiler checks that shared data is protected (`Send`/`Sync`, critical
  sections), which removes a whole class of "forgot the mutex" bugs.
- The **`critical-section`** crate gives one portable way to say "disable
  interrupts while this runs", which libraries use so they work on any
  chip.

## 8. "How do you test `no_std` code without hardware?"

**Answer:**

- **On the host.** A `no_std` **library** still tests with the normal test
  harness, because the harness links `std`. The sample's two tests ran with
  plain `cargo test` (and again with `--features alloc`) and passed:

```text
test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
```

- **Keep logic separate from hardware.** Put algorithms (a ring buffer, a
  parser, a state machine) in a `no_std` library; put register access in a
  thin layer. Test the first on the host, and swap the second with a
  **mock** that implements the `embedded-hal` traits.
- **Emulator:** run the real firmware in **QEMU** (it supports some
  Cortex-M boards) or **Renode**, in CI, with no board.
- **On the device:** `defmt-test` runs `#[test]` functions on real hardware
  and reports through the probe. **Hardware-in-the-loop** CI runners keep a
  board attached.
- Use **Miri** for the `unsafe` parts of the library on the host (see
  [Unsafe Rust & Miri](../advanced-language/rust-unsafe-and-miri.md)).

## 9. "Where do people actually use `no_std` besides microcontrollers?"

**Answer:**

- **Operating-system kernels** and bootloaders (the Linux kernel accepts
  Rust drivers; they use `core` and a kernel-specific `alloc`).
- **WebAssembly** modules that must be tiny: see
  [Rust & WebAssembly §6](rust-webassembly.md#6-how-do-you-make-a-webassembly-file-small).
- **Libraries meant to run anywhere**: parsers, encoders, protocol
  implementations (`serde` and `postcard` have `no_std` modes).
- **Security-critical code** where the surface of the runtime must be
  small.
- Even if you never target a chip, writing a library as `no_std` is a
  discipline: no hidden allocation or OS calls.

## 10. "How do AI tools help or hurt here?"

**Answer:**

- **Help:**
    - Ask for the **boilerplate** around a board: `memory.x`, a
      `.cargo/config.toml` with a probe-rs runner, a `cortex-m-rt` entry.
    - Ask it to translate a vendor C example (register writes) into the
      **HAL** calls for your chip's crate.
    - Ask it to list which standard types have a `no_std` replacement.
- **Hurt:**
    - Embedded crates **change often** and are split by chip generation. An
      AI frequently mixes **old and new** `embedded-hal` (0.2 vs 1.0)
      traits or names a HAL version that does not exist. Check the
      versions with `cargo add`, then compile.
    - It cannot see **your board**. Pin numbers, clock settings, and
      memory sizes it supplies are guesses; a wrong clock setting can
      appear to work and then misbehave.
    - It may use `std` types (`HashMap`, `String`, `println!`) in
      `no_std` code. The compiler catches that (§2); make it fix the
      error with a `no_std` type rather than adding `std`.
- See [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

## 11. Interview Questions You're Likely to Get Asked

**Basics**

- "What is the difference between `core`, `alloc`, and `std`?" — expects:
  no OS or heap / needs a heap / needs an OS; `std` re-exports the others,
  [§1](#1-what-are-core-alloc-and-std).
- "Why is `HashMap` not in `alloc`?" — expects: its default hasher needs OS
  randomness; use `BTreeMap` or `hashbrown`, [§1](#1-what-are-core-alloc-and-std).
- "What do you lose and keep with `#![no_std]`?" — expects: lose OS and heap
  features, keep the whole language, [§2](#2-what-do-you-lose-with-no_std).

**Binaries**

- "Why does a `no_std` binary need `#[panic_handler]`?" — expects: no runtime
  decides what a panic does; one handler, defined by the binary, not a
  library, [§3](#3-what-is-no_main-and-why-does-a-binary-need-a-panic-handler).
- "How do you use `Vec` without `std`?" — expects: `extern crate alloc` plus a
  `#[global_allocator]`; or `heapless`,
  [§4](#4-how-do-you-use-vec-and-box-without-an-os).

**Hardware**

- "Why use `read_volatile` for a register?" — expects: stops the compiler
  from removing or merging reads; `unsafe` because the address is unchecked,
  [§5](#5-how-do-you-talk-to-hardware).
- "What are PAC, HAL, and `embedded-hal`?" — expects: generated registers,
  friendly chip API, shared traits for portable drivers,
  [§5](#5-how-do-you-talk-to-hardware).
- "How does Rust prevent two drivers from using the same pin?" — expects:
  peripherals taken once, ownership and typestate, [§5](#5-how-do-you-talk-to-hardware).

**Design and testing**

- "Embassy or RTIC?" — expects: async tasks and an executor vs
  interrupt-driven tasks with compile-time priorities, [§7](#7-what-are-embassy-and-rtic).
- "How do you test firmware without the board?" — expects: logic in a
  `no_std` library tested on the host, mocks of `embedded-hal`, QEMU,
  [§8](#8-how-do-you-test-no_std-code-without-hardware).

---

## Code Samples

All files are in `code_samples/rust/nostd_demo/` (its own package) and were
run on Rust 1.99.1.

- `src/lib.rs` — `#![no_std]` ring buffer (`Ring<T, N>`), a feature-gated
  `alloc` function, `read_reg` with `read_volatile`, and two unit tests.
- `compile_fail/uses_std_in_no_std.rs` — must fail: `Vec`, `println!`.
- `compile_fail/no_panic_handler.rs` — must fail: no `#[panic_handler]`.
- `compile_fail/no_global_allocator.rs` — must fail: `alloc` without an
  allocator.

```bash
cd code_samples/rust/nostd_demo
rustup target add thumbv7em-none-eabihf
cargo build --release --target thumbv7em-none-eabihf
cargo build --release --target thumbv7em-none-eabihf --features alloc
cargo test
rustc --edition 2024 --crate-type=lib --emit=metadata -o /tmp/out compile_fail/uses_std_in_no_std.rs
rustc --edition 2024 --target thumbv7em-none-eabihf -C panic=abort --crate-type=bin compile_fail/no_panic_handler.rs
rustc --edition 2024 --target thumbv7em-none-eabihf -C panic=abort --crate-type=staticlib compile_fail/no_global_allocator.rs
```
