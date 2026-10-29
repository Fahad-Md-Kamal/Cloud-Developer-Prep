//! Modules, visibility, `use` and re-exports, in one file.
//! Run: cargo run --example modules_visibility

mod bank {
    pub mod rates {
        pub const FEE: i64 = 2;
        pub fn interest(balance: i64) -> i64 {
            balance / 100
        }
    }

    // Re-export: callers can write `bank::DEFAULT_FEE` without knowing about `rates`.
    pub use self::rates::FEE as DEFAULT_FEE;

    pub struct Account {
        pub owner: String, // public field
        balance: i64,      // private: only this module (and its children) can touch it
    }

    impl Account {
        pub fn open(owner: &str, deposit: i64) -> Self {
            Account { owner: owner.to_string(), balance: deposit }
        }
        pub fn balance(&self) -> i64 {
            self.balance
        }
        pub fn deposit(&mut self, n: i64) {
            self.balance += n - internal::fee();
        }
        pub fn add_interest(&mut self) {
            self.balance += rates::interest(self.balance);
        }
    }

    // pub(crate): visible anywhere in this crate, but not to other crates.
    pub(crate) fn audit(a: &Account) -> String {
        format!("{}:{}", a.owner, a.balance)
    }

    mod internal {
        // pub(super): visible to the parent module only.
        pub(super) fn fee() -> i64 {
            super::DEFAULT_FEE
        }
    }
}

use bank::Account;

fn main() {
    let mut a = Account::open("ann", 1000);
    a.deposit(500);
    a.add_interest();
    println!("{} has {}", a.owner, a.balance());
    println!("audit = {}", bank::audit(&a));
    println!("fee = {}", bank::DEFAULT_FEE);
    // a.balance = 0;              // error[E0616]: field `balance` is private
    // bank::internal::fee();       // error[E0603]: module `internal` is private
}
