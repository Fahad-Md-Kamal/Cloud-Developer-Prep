//! Capstone 4: an HTTP/1.1 server built on `std::net` only.
//! Concepts: `TcpListener`, `Read`/`Write`, parsing bytes, threads, `Result`.

use std::net::TcpListener;

#[derive(Debug, PartialEq, Eq)]
pub struct Request {
    pub method: String,
    pub path: String,
    pub headers: Vec<(String, String)>,
}

/// Parse the request line and headers from the bytes read so far.
/// Return `None` if the header block is not complete yet (no blank line seen).
pub fn parse_request(_raw: &[u8]) -> Option<Request> {
    todo!("find \\r\\n\\r\\n, split lines, split on ': '")
}

/// Render a response with a correct `Content-Length`.
pub fn response(_status: u16, _reason: &str, _body: &str) -> Vec<u8> {
    todo!()
}

/// Accept connections forever and answer each with a handler on a worker thread.
pub fn serve(_listener: TcpListener, _handler: fn(&Request) -> Vec<u8>) -> std::io::Result<()> {
    todo!("start with a thread per connection, then reuse capstone 6")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    #[ignore = "c04: implement parse_request"]
    fn c04_parses_request_line_and_headers() {
        let raw = b"GET /hello HTTP/1.1\r\nHost: example.com\r\n\r\n";
        let r = parse_request(raw).unwrap();
        assert_eq!((r.method.as_str(), r.path.as_str()), ("GET", "/hello"));
        assert_eq!(r.headers, [("Host".to_string(), "example.com".to_string())]);
    }

    #[test]
    #[ignore = "c04: implement parse_request"]
    fn c04_incomplete_headers_return_none() {
        assert_eq!(parse_request(b"GET / HTTP/1.1\r\nHost: x"), None);
    }

    #[test]
    #[ignore = "c04: implement response"]
    fn c04_response_has_content_length() {
        let out = String::from_utf8(response(200, "OK", "hi")).unwrap();
        assert!(out.starts_with("HTTP/1.1 200 OK\r\n"));
        assert!(out.contains("Content-Length: 2\r\n"));
        assert!(out.ends_with("\r\n\r\nhi"));
    }
}
