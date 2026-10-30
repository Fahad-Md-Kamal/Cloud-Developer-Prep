//! Capstone 3: a key-value store with a write-ahead log (WAL).
//! Concepts: `std::fs`, `BufWriter`, error enums, `HashMap`, recovery, `Drop`.

use std::path::Path;

#[derive(Debug)]
pub enum KvError {
    Io(std::io::Error),
    Corrupt { line: usize },
}

impl From<std::io::Error> for KvError {
    fn from(e: std::io::Error) -> Self {
        KvError::Io(e)
    }
}

pub struct KvStore {
    // Fields are yours to design: an in-memory map plus an open log file.
}

impl KvStore {
    /// Open the store, replaying the log at `dir/store.wal` (create it if missing).
    pub fn open(_dir: &Path) -> Result<Self, KvError> {
        todo!("replay the log into memory")
    }
    /// Append `SET key value` to the log (flush it), then update memory.
    pub fn set(&mut self, _key: &str, _value: &str) -> Result<(), KvError> {
        todo!()
    }
    pub fn get(&self, _key: &str) -> Option<&str> {
        todo!()
    }
    /// Append `DEL key` to the log, then update memory. Returns whether the key existed.
    pub fn delete(&mut self, _key: &str) -> Result<bool, KvError> {
        todo!()
    }
    /// Rewrite the log with only live keys (stretch goal: do it atomically with rename).
    pub fn compact(&mut self) -> Result<(), KvError> {
        todo!()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn temp_dir(name: &str) -> std::path::PathBuf {
        let d = std::env::temp_dir().join(format!("capstone_kv_{name}_{}", std::process::id()));
        std::fs::create_dir_all(&d).unwrap();
        d
    }

    #[test]
    #[ignore = "c03: implement KvStore"]
    fn c03_survives_restart() {
        let dir = temp_dir("restart");
        {
            let mut s = KvStore::open(&dir).unwrap();
            s.set("a", "1").unwrap();
            s.set("b", "2").unwrap();
            s.delete("a").unwrap();
        }
        let s = KvStore::open(&dir).unwrap();
        assert_eq!(s.get("a"), None);
        assert_eq!(s.get("b"), Some("2"));
    }

    #[test]
    #[ignore = "c03: implement KvStore"]
    fn c03_compaction_keeps_data() {
        let dir = temp_dir("compact");
        let mut s = KvStore::open(&dir).unwrap();
        for i in 0..100 {
            s.set("k", &i.to_string()).unwrap();
        }
        s.compact().unwrap();
        assert_eq!(s.get("k"), Some("99"));
        assert!(std::fs::metadata(dir.join("store.wal")).unwrap().len() < 100);
    }
}
