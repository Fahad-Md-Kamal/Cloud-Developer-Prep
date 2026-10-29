struct Parser<'src> {
    rest: &'src str,
}

impl<'src> Parser<'src> {
    // Returns a borrow tied to `&mut self`, not to the source text.
    fn next_token(&mut self) -> Option<&str> {
        let rest = self.rest.trim_start();
        let end = rest.find(' ').unwrap_or(rest.len());
        if end == 0 {
            return None;
        }
        let (tok, tail) = rest.split_at(end);
        self.rest = tail;
        Some(tok)
    }
}

fn main() {
    let mut p = Parser { rest: "a b" };
    let t1 = p.next_token();
    let t2 = p.next_token();
    println!("{t1:?} {t2:?}");
}
