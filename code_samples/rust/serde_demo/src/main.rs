//! Serde demo: derive attributes, zero-copy borrowing, formats, a custom
//! deserializer. Run: `cargo run` inside `code_samples/rust/serde_demo`.

use serde::de::{self, Visitor};
use serde::{Deserialize, Deserializer, Serialize};
use std::borrow::Cow;
use std::fmt;
use std::time::Duration;

#[derive(Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct User {
    user_name: String,
    #[serde(default)]
    admin: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    nickname: Option<String>,
    #[serde(flatten)]
    extra: std::collections::BTreeMap<String, serde_json::Value>,
}

#[derive(Debug, PartialEq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
enum Event {
    Login { user: String },
    Logout { user: String },
    Ping,
}

#[derive(Serialize)]
enum External {
    Login { user: String },
}

#[derive(Serialize)]
#[serde(tag = "t", content = "c")]
enum Adjacent {
    Login { user: String },
}

#[derive(Serialize)]
#[serde(untagged)]
enum Untag {
    Login { user: String },
}

#[derive(Debug, PartialEq, Serialize, Deserialize)]
#[serde(untagged)]
enum IdOrName {
    Id(u64),
    Name(String),
}

// Zero-copy: `name` borrows from the input text when no escapes are present.
#[derive(Debug, Deserialize)]
struct Borrowed<'a> {
    #[serde(borrow)]
    name: Cow<'a, str>,
    tag: &'a str,
}

// A custom deserializer: "1500ms" or "2s" into a Duration.
fn de_duration<'de, D: Deserializer<'de>>(d: D) -> Result<Duration, D::Error> {
    struct V;
    impl Visitor<'_> for V {
        type Value = Duration;
        fn expecting(&self, f: &mut fmt::Formatter) -> fmt::Result {
            f.write_str("a string like \"1500ms\" or \"2s\"")
        }
        fn visit_str<E: de::Error>(self, s: &str) -> Result<Duration, E> {
            if let Some(n) = s.strip_suffix("ms") {
                n.parse().map(Duration::from_millis).map_err(E::custom)
            } else if let Some(n) = s.strip_suffix('s') {
                n.parse().map(Duration::from_secs).map_err(E::custom)
            } else {
                Err(E::invalid_value(de::Unexpected::Str(s), &self))
            }
        }
    }
    d.deserialize_str(V)
}

#[derive(Debug, Deserialize)]
struct Config {
    #[serde(deserialize_with = "de_duration")]
    timeout: Duration,
}

fn parse_owned<T: serde::de::DeserializeOwned>(s: &str) -> serde_json::Result<T> {
    serde_json::from_str(s)
}

fn main() {
    let json = r#"{"userName":"demo","region":"eu","level":3}"#;
    let u: User = serde_json::from_str(json).unwrap();
    println!("{u:?}");
    println!("{}", serde_json::to_string(&u).unwrap());

    for e in [Event::Login { user: "a".into() }, Event::Ping] {
        let s = serde_json::to_string(&e).unwrap();
        println!("{s}  ->  {:?}", serde_json::from_str::<Event>(&s).unwrap());
    }

    println!(
        "{}",
        serde_json::to_string(&External::Login { user: "a".into() }).unwrap()
    );
    println!(
        "{}",
        serde_json::to_string(&Adjacent::Login { user: "a".into() }).unwrap()
    );
    println!(
        "{}",
        serde_json::to_string(&Untag::Login { user: "a".into() }).unwrap()
    );
    println!(
        "{:?}",
        serde_json::from_str::<Vec<IdOrName>>(r#"[7,"seven"]"#).unwrap()
    );
    println!("{}", serde_json::from_str::<IdOrName>("true").unwrap_err());

    let text = r#"{"name":"plain","tag":"t"}"#;
    let b: Borrowed = serde_json::from_str(text).unwrap();
    println!(
        "borrowed? {} (tag={})",
        matches!(b.name, Cow::Borrowed(_)),
        b.tag
    );
    let b2: Borrowed = serde_json::from_str(r#"{"name":"a\nb","tag":"t"}"#).unwrap();
    println!(
        "with escape borrowed? {}",
        matches!(b2.name, Cow::Borrowed(_))
    );
    // `&str` field + escape = runtime error
    println!(
        "{}",
        serde_json::from_str::<Borrowed>(r#"{"name":"x","tag":"a\nb"}"#).unwrap_err()
    );

    let c: Config = serde_json::from_str(r#"{"timeout":"1500ms"}"#).unwrap();
    println!("{:?}", c.timeout);
    println!(
        "{}",
        serde_json::from_str::<Config>(r#"{"timeout":"5m"}"#).unwrap_err()
    );

    let owned: Event = parse_owned(r#"{"type":"logout","user":"z"}"#).unwrap();
    println!("{owned:?}");

    // Formats: same value, different bytes.
    let ev = Event::Login {
        user: "demo".into(),
    };
    let j = serde_json::to_vec(&ev).unwrap();
    let m = rmp_serde::to_vec_named(&ev).unwrap();
    let p = postcard::to_stdvec(&ev).unwrap();
    println!(
        "json={}B msgpack={}B postcard={}B",
        j.len(),
        m.len(),
        p.len()
    );
    println!("postcard bytes: {p:?}");
    println!(
        "postcard back: {}",
        postcard::from_bytes::<Event>(&p).unwrap_err()
    );
    println!(
        "{}",
        toml::to_string(&Config2 {
            name: "x".into(),
            retries: 3
        })
        .unwrap()
    );
    println!(
        "{}",
        serde_json::from_str::<Strict>(r#"{"port":80,"prot":1}"#).unwrap_err()
    );
    println!(
        "{}",
        serde_json::from_str::<Strict>(r#"{"port":70000}"#).unwrap_err()
    );
    println!("{}", serde_json::from_str::<Strict>("{}").unwrap_err());
    // Untrusted input: deep nesting is rejected by serde_json's recursion limit.
    let deep = "[".repeat(1000) + &"]".repeat(1000);
    println!(
        "{}",
        serde_json::from_str::<serde_json::Value>(&deep).unwrap_err()
    );
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
#[allow(dead_code)]
struct Strict {
    port: u16,
}

#[derive(Serialize)]
struct Config2 {
    name: String,
    retries: u32,
}
