pub struct Config { pub name: String, pub retries: u32 }
pub fn connect(cfg: &Config, verbose: bool) -> bool { verbose || !cfg.name.is_empty() }
