//! Capstone 2: a tiny Markdown-to-HTML converter.
//! Concepts: enums, `match`, parsing with iterators, `String` building, escaping.

/// Convert a small Markdown subset to HTML:
/// `# heading` (1 to 3 levels), paragraphs, `**bold**`, `*italic*`, `` `code` ``,
/// and `- list items`. Escape `<`, `>` and `&` in text.
pub fn to_html(_markdown: &str) -> String {
    todo!("block parser first, inline parser second")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    #[ignore = "c02: implement to_html"]
    fn c02_heading_and_paragraph() {
        assert_eq!(to_html("# Hi\n\nhello"), "<h1>Hi</h1>\n<p>hello</p>\n");
    }

    #[test]
    #[ignore = "c02: implement to_html"]
    fn c02_inline_and_escape() {
        assert_eq!(
            to_html("a **b** <c>"),
            "<p>a <strong>b</strong> &lt;c&gt;</p>\n"
        );
    }

    #[test]
    #[ignore = "c02: implement to_html"]
    fn c02_list() {
        assert_eq!(to_html("- a\n- b"), "<ul>\n<li>a</li>\n<li>b</li>\n</ul>\n");
    }
}
