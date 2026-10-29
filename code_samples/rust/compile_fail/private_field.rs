mod bank {
    pub struct Account {
        balance: i64,
    }
    impl Account {
        pub fn open() -> Self {
            Account { balance: 0 }
        }
    }
}

fn main() {
    let mut a = bank::Account::open();
    a.balance = 100;
}
