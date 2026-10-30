// A sealed trait cannot be implemented outside its module/crate: the supertrait is private.
mod api {
    mod private {
        pub trait Sealed {}
    }
    pub trait Closed: private::Sealed {}
    pub struct Mine;
    impl private::Sealed for Mine {}
    impl Closed for Mine {}
}

struct Other;
impl api::Closed for Other {}

fn main() {}
