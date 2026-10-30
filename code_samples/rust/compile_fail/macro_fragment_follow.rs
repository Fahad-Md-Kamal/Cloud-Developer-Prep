// Follow-set rule: after `$e:expr` only `=>`, `,` or `;` may follow.
macro_rules! bad {
    ($e:expr $f:expr) => {
        $e + $f
    };
}

fn main() {}
