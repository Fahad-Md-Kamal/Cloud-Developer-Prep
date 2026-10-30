---
title: Serde and Serialization
---

# Serde and Serialization

**Serialization** turns a value in memory into bytes or text (JSON,
TOML, a binary format). **Deserialization** does the reverse. In Rust both
are done by **Serde**, whose key idea is a **split**: your types describe
themselves once (the `Serialize` and `Deserialize` traits), and each file
format is a separate crate that knows how to read and write the Serde
**data model**. Any type works with any format. That is why one
`#[derive(Serialize, Deserialize)]` gives you JSON, TOML, MessagePack and
more.

!!! note "Version"
    Written for **Rust 1.99** and the **2024 edition**. Sample run with
    `serde` 1.0.229, `serde_json` 1.0.154, `toml` 1.1.8, `rmp-serde` 1.3.1
    and `postcard` 1.1.3. All outputs below are real output from
    `code_samples/rust/serde_demo/`.

## 1. "How does Serde work? What is the data model?"

**Answer:**

- Two sides that never know each other:

| Side | Traits | Written by |
|---|---|---|
| Your types | `Serialize`, `Deserialize<'de>` | You, usually with `#[derive]` |
| The format | `Serializer`, `Deserializer<'de>` | The format crate (`serde_json`, `toml`, `postcard`) |

- The **data model** is the shared vocabulary between them: about 29
  types such as integers, strings, `Option`, sequences, maps, structs,
  and enum variants. A struct is "a map with known keys"; a `Vec<T>` is
  "a sequence".
- **Serializing** is simple: the type calls methods on the `Serializer`
  (`serialize_struct`, `serialize_field`, ...) in order. No allocation is
  needed.
- **Deserializing** uses the **visitor** pattern. The *format* knows what
  is in the input, the *type* knows what it wants. The type hands the
  format a `Visitor`; the format calls `visit_str`, `visit_u64`,
  `visit_map` and so on, depending on what it finds. The visitor builds
  the value or fails with an error.
- Because of the visitor, deserializing can **reject** things (wrong
  type, missing field) with a clear message, and can **borrow** from the
  input (§5).
- Nothing is reflection. `#[derive]` generates normal Rust code at compile
  time (see [Macros](../advanced-language/rust-macros.md)), so the result
  is fast and has no runtime type information.

## 2. "Which attributes do I use every day?"

```rust
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
```

Real result for the input `{"userName":"demo","region":"eu","level":3}`:

```text
User { user_name: "demo", admin: false, nickname: None, extra: {"level": Number(3), "region": String("eu")} }
{"userName":"demo","admin":false,"level":3,"region":"eu"}
```

**Answer:**

- `rename_all = "camelCase"` renames fields on the wire. Your Rust names
  stay `snake_case`. Other cases: `snake_case`, `kebab-case`,
  `SCREAMING_SNAKE_CASE`, `PascalCase`. `rename = "x"` renames one field.
- `default` fills a missing field with `Default::default()` (above,
  `admin` became `false`). Without it, a missing field is an error.
- `skip_serializing_if = "Option::is_none"` leaves a `None` out of the
  output instead of writing `null`.
- `flatten` merges a nested struct or map into the parent. Above, the
  unknown keys `region` and `level` landed in `extra`. This is how you
  keep "everything else" without losing it on a round trip.
- `deny_unknown_fields` turns an unknown key into an error. Real output:

```text
unknown field `prot`, expected `port` at line 1 column 17
```

  Good for configuration files (a typo should fail loudly). Not good for
  public APIs that must accept newer clients. It cannot be combined with
  `flatten`.
- Typed numbers are checked: `{"port":70000}` into a `u16` gives
  `invalid value: integer `70000`, expected u16`. A missing field gives
  `missing field `port``.
- `alias`, `skip`, `with`, `serialize_with` and `deserialize_with`
  cover the remaining cases (§6).

## 3. "How are enums represented, and which form should I pick?"

```rust
#[derive(Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
enum Event {
    Login { user: String },
    Logout { user: String },
    Ping,
}
```

Real output:

```text
{"type":"login","user":"a"}  ->  Login { user: "a" }
{"type":"ping"}  ->  Ping
```

**Answer:**

- Serde has **four** enum forms. Same enum, different JSON for `Login`
  (shapes checked by running the sample; the example above adds
  `rename_all`, so it writes `login` in lowercase):

| Attribute | JSON for `Login { user: "a" }` | Notes |
|---|---|---|
| none (**externally tagged**, the default) | `{"Login":{"user":"a"}}` | Works with every format (the default) |
| `#[serde(tag = "type")]` (**internally tagged**) | `{"type":"Login","user":"a"}` | The common REST/JSON style; struct, unit and newtype-of-struct variants, but not tuple variants (a compile error) |
| `#[serde(tag = "t", content = "c")]` (**adjacently tagged**) | `{"t":"Login","c":{"user":"a"}}` | Works with tuple variants too |
| `#[serde(untagged)]` | `{"user":"a"}` | Tries each variant in order; first match wins |

- **`untagged` has a cost.** The input is **buffered**, each variant is
  tried in turn, and the error message loses detail. Real output for the
  input `true` against `enum IdOrName { Id(u64), Name(String) }`:

```text
data did not match any variant of untagged enum IdOrName
```

  It does not say why. Use `untagged` only when the wire format is fixed
  by someone else.
- **Internally tagged and `flatten` also buffer** the input into an
  intermediate value. That is fine for JSON. It is why they **do not work
  with non-self-describing formats**, as the next section shows.
- Variant order matters for `untagged`: put the most specific variant
  first.

## 4. "Which formats exist, and how do they differ?"

```text
json=30B msgpack=22B postcard=11B       (the value Event::Login { user: "demo" })
postcard bytes: [5, 108, 111, 103, 105, 110, 4, 100, 101, 109, 111]
postcard back: This is a feature that PostCard will never implement
```

**Answer:**

| Format | Crate | Human readable | Self-describing | Use it for |
|---|---|---|---|---|
| JSON | `serde_json` | Yes | Yes | APIs, logs, anything shown to humans or other languages |
| TOML | `toml` | Yes | Yes | Configuration files |
| YAML | (see note below) | Yes | Yes | Configuration |
| MessagePack | `rmp-serde` | No | Yes | JSON-shaped data, smaller and faster, many languages |
| postcard | `postcard` | No | **No** | Embedded and Rust-to-Rust, very small |

- **YAML:** the best-known crate, `serde_yaml`, says in its README that it is
  **no longer maintained**. Check which YAML crate is currently maintained
  before you choose one. This page does not recommend a specific one.
- **Self-describing** means the bytes say what type each value has (a
  JSON string looks different from a number). **Non-self-describing**
  formats write only the values; both sides must already know the type.
  They are smaller, but anything that needs the format to "look ahead"
  fails.
- The sample shows it: `postcard` **writes** the internally tagged
  `Event` fine (11 bytes, against 30 for JSON), but **cannot read it
  back**. Internally tagged enums need the format to look at the data
  first. The message is `This is a feature that PostCard will never
  implement`. Use an externally tagged enum for such formats.
- Use `rmp_serde::to_vec_named` to write struct **field names**; the
  default writes structs as arrays and breaks if you reorder fields.
- A binary format is a **contract between versions**. Adding a field to a
  postcard struct changes the bytes. For anything stored on disk or sent
  between versions, add an explicit version number or use a self-describing
  format.
- TOML cannot represent everything JSON can (no top-level array, no
  `null`). Real TOML output from the sample:

```text
name = "x"
retries = 3
```

## 5. "What is zero-copy deserialization, and what is `DeserializeOwned`?"

```rust
#[derive(Debug, Deserialize)]
struct Borrowed<'a> {
    #[serde(borrow)]
    name: Cow<'a, str>,
    tag: &'a str,
}
```

Real output:

```text
borrowed? true (tag=t)
with escape borrowed? false
invalid type: string "a\nb", expected a borrowed string at line 1 column 24
```

**Answer:**

- **Zero-copy** means the parsed value **points into the input text**
  instead of allocating a new `String`. The trait is
  `Deserialize<'de>`; the `'de` lifetime is "how long the input lives".
  (Lifetimes: [Lifetimes §1](../foundations/rust-lifetimes.md#1-what-is-a-lifetime-really).)
- A `&'a str` field borrows from the input. It is fast, but the input
  must stay alive as long as the value, and it **fails** if the text has
  to be changed. A JSON string with an escape such as `\n` is not
  identical to the raw bytes, so a `&str` cannot hold it. The third line
  above is that real failure, **at runtime**, on valid JSON.
- **`Cow<'a, str>` with `#[serde(borrow)]`** is the safe version: it
  borrows when it can (`borrowed? true`) and allocates only when it must
  (`with escape borrowed? false`). `#[serde(borrow)]` is required for
  `Cow`, otherwise Serde always makes it owned.
- **`DeserializeOwned`** means `for<'de> Deserialize<'de>`: "can be built
  from input of **any** lifetime", so the value does not borrow from the
  input at all. Use it for functions that read from a file or socket and
  drop the buffer (see
  [Lifetimes §7](../foundations/rust-lifetimes.md#7-what-is-a-higher-ranked-bound-fora)).
  Typical signature: `fn parse<T: DeserializeOwned>(s: &str) -> Result<T>`.
- Rule of thumb: use owned types (`String`) by default. Use borrowing only
  after measuring that allocation is a bottleneck (see
  [Performance Engineering](../performance-and-internals/rust-performance-engineering.md)).

## 6. "How do I write a custom (de)serializer?"

```rust
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

#[derive(Deserialize)]
struct Config {
    #[serde(deserialize_with = "de_duration")]
    timeout: Duration,
}
```

Real output:

```text
1.5s
invalid value: string "5m", expected a string like "1500ms" or "2s" at line 1 column 15
```

**Answer:**

- **For one field:** `deserialize_with = "function"` (and
  `serialize_with`). The function receives the `Deserializer` and returns
  the value. This is the common case and needs no trait impl.
- **For a whole type:** implement `Serialize` or `Deserialize` by hand.
  Inside, a `Visitor` says what shapes it accepts (`visit_str`,
  `visit_u64`, `visit_map`, ...) and `expecting` describes them. That
  description is what appears in the error message above.
- Report errors with `E::custom(..)` or the typed helpers
  (`invalid_value`, `invalid_length`, `missing_field`). Never `panic!` in a
  deserializer; the input is untrusted.
- Before writing a visitor, check the crate **`serde_with`**, which has
  ready-made adapters (durations, comma-separated lists, base64). Do not
  hand-write what a maintained crate already covers.
- To change the whole shape of a type through a simpler one, use
  `#[serde(from = "Other")]`, `#[serde(try_from = "Other")]` and
  `#[serde(into = "Other")]`. `try_from` is the neat way to run
  **validation** while parsing (the parsed value is an `Other`, converted
  with `TryFrom`, which can fail). It keeps invalid values from ever
  existing, the same idea as the validated `Quantity` type in
  [Project Architecture](rust-project-architecture-and-api-design.md).

## 7. "How do I handle untrusted input safely?"

**Answer:**

- Deserializing is parsing, and parsing attacker data is a security
  boundary. Deserialize into **specific types**, not a `Value` tree, so
  invalid shapes are rejected early.
- **Limit size before parsing.** Serde does not limit how large an input is.
  Put a request body limit in front (see
  [Web Services with Axum §6](rust-web-services-with-axum.md#6-how-does-middleware-work-what-is-a-tower-layer)).
- **Nesting.** `serde_json` has a recursion limit of 128 levels. A
  1,000-level `[[[[...]]]]` returns an error and does not overflow the
  stack. Real output:

```text
recursion limit exceeded at line 1 column 128
```

  (`serde_json` has a feature, `unbounded_depth`, that removes the limit.
  Do not enable it for untrusted input.)
- **Validate after parsing.** Types check the shape, not the meaning:
  a `u16` port can still be `0`, a string can be empty. Use `try_from`
  (§6) or a `validate()` step.
- **Do not trust the integer sizes** to protect you from huge allocations
  in binary formats: a length prefix can claim a gigabyte. Check each
  format crate's documentation for limits, and cap input size.
- **`deny_unknown_fields`** helps for configuration; leave it off for
  APIs that must tolerate additions.

## 8. "How do AI tools help or hurt with Serde?"

**Answer:**

- Good for: writing derive attributes, mapping an example JSON payload to
  structs, and writing round-trip tests.
- They give an `untagged` enum or `serde_json::Value` as an easy answer.
  Both lose type safety and error detail. Ask for a tagged enum and a
  typed struct.
- They write `#[serde(borrow)]` or `&str` fields that fail only when an
  input contains an escape. If a zero-copy struct "works in tests", test
  an escaped string.
- When an API's JSON is inconsistent, they guess the shape from one
  example. Paste **several** real examples, including the nulls.
- See [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

## 9. Interview Questions You're Likely to Get Asked

**Concepts**

- "How does Serde work without reflection?" — expects the derive
  generates code, the data model sits between types and formats,
  [§1](#1-how-does-serde-work-what-is-the-data-model).
- "What is a visitor?" — expects the type's object that the format calls
  with whatever it finds,
  [§1](#1-how-does-serde-work-what-is-the-data-model).
- "What does self-describing mean?" — expects values carry their own
  type markers; postcard and bincode do not,
  [§4](#4-which-formats-exist-and-how-do-they-differ).

**Practical**

- "How do you keep unknown fields on a round trip?" — expects
  `#[serde(flatten)]` into a map,
  [§2](#2-which-attributes-do-i-use-every-day).
- "Which enum representation would you pick for a REST API?" — expects
  internally tagged, and why `untagged` is a last resort,
  [§3](#3-how-are-enums-represented-and-which-form-should-i-pick).
- "Why does a `&str` field sometimes fail on valid JSON?" — expects
  escapes force a copy; use `Cow` with `#[serde(borrow)]`,
  [§5](#5-what-is-zero-copy-deserialization-and-what-is-deserializeowned).
- "What is `DeserializeOwned`?" — expects `for<'de> Deserialize<'de>`,
  [§5](#5-what-is-zero-copy-deserialization-and-what-is-deserializeowned).
- "How do you validate while deserializing?" — expects `try_from` or
  `deserialize_with`,
  [§6](#6-how-do-i-write-a-custom-deserializer).

**Security**

- "How do you deserialize untrusted JSON safely?" — expects typed targets,
  size limit, recursion limit, validation after parsing,
  [§7](#7-how-do-i-handle-untrusted-input-safely).

---

## Code Samples

Package `code_samples/rust/serde_demo/` (own `Cargo.toml`; Rust 1.99.1).

- `src/main.rs` — every example on this page: attributes, the four enum
  forms, borrowing,
  a custom deserializer, four formats, `deny_unknown_fields`, and the
  recursion limit.

```bash
cd code_samples/rust/serde_demo
cargo run
```
