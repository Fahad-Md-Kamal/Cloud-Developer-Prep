//! Deliberate undefined behaviour, to be run ONLY under Miri:
//!     cargo +nightly miri run --example ub_cases -- <case>
//! cases: oob  uaf  bool  alias  uninit  align  dangling-ref  race  transmute-ptr  ok
//! Running these on a normal build is undefined behaviour: anything may happen.

use std::mem::MaybeUninit;

fn main() {
    let case = std::env::args().nth(1).unwrap_or_else(|| "ok".into());
    match case.as_str() {
        // 1. out-of-bounds read through a raw pointer
        "oob" => {
            let v = vec![1u8, 2, 3];
            let p = v.as_ptr();
            let x = unsafe { *p.add(3) };
            println!("read {x}");
        }
        // 2. use after free through a raw pointer
        "uaf" => {
            let p: *const i32 = {
                let b = Box::new(42);
                &*b as *const i32
            };
            let x = unsafe { *p };
            println!("read {x}");
        }
        // 3. invalid value: a bool must be 0 or 1
        "bool" => {
            let b: bool = unsafe { std::mem::transmute(3u8) };
            println!("{}", b);
        }
        // 4. aliasing violation: using an old raw pointer after a newer &mut was used
        "alias" => {
            let mut x = 10;
            let raw = &mut x as *mut i32;
            let r1 = unsafe { &mut *raw };
            let r2 = unsafe { &mut *raw };
            *r2 = 2;
            *r1 = 1; // r1 was invalidated when r2 was created and used
            println!("{x}");
        }
        // 5. reading uninitialized memory
        "uninit" => {
            let m: MaybeUninit<u32> = MaybeUninit::uninit();
            let x = unsafe { m.assume_init() };
            println!("{x}");
        }
        // 6. misaligned pointer read
        "align" => {
            let bytes = [0u8; 8];
            let p = unsafe { bytes.as_ptr().add(1) } as *const u32;
            let x = unsafe { *p };
            println!("{x}");
        }
        // 7. a dangling reference is UB to CREATE, even if it is never read
        "dangling-ref" => {
            let r: &i32 = unsafe { &*std::ptr::without_provenance::<i32>(4) };
            let _ = r;
        }
        // 8. data race between two threads
        "race" => {
            static mut N: u32 = 0;
            let t = std::thread::spawn(|| unsafe { *(&raw mut N) += 1 });
            unsafe { *(&raw mut N) += 1 };
            t.join().unwrap();
        }
        // 9. integer-to-pointer transmute loses provenance
        #[allow(integer_to_ptr_transmutes)]
        "transmute-ptr" => {
            let x = 5i32;
            let addr = &x as *const i32 as usize;
            let p: *const i32 = unsafe { std::mem::transmute(addr) };
            println!("{}", unsafe { *p });
        }
        _ => println!("ok: nothing undefined here"),
    }
}
