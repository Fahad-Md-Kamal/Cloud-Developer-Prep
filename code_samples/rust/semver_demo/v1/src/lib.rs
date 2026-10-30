pub struct Config { pub name: String }
pub fn connect(cfg: &Config) -> bool { !cfg.name.is_empty() }
pub fn old_helper() {}
