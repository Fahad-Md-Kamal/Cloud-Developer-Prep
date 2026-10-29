static mut COUNTER: u32 = 0;

fn main() {
    unsafe {
        let r = &mut COUNTER;
        *r += 1;
    }
}
