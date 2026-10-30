// A GAT whose item borrows from `self` needs `where Self: 'a`.
trait Lending {
    type Item<'a>;
    fn next<'a>(&'a mut self) -> Option<Self::Item<'a>>;
}

fn main() {}
