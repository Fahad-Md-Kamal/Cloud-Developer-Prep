---
title: "How the Internet Moves Files: TCP, HTTP Transfer Mechanics & Streaming"
---

# How the Internet Moves Files: TCP, HTTP Transfer Mechanics & Streaming

Knowing `requests.post(url, files=...)` or an `<input type="file">` tag
is the tool-usage version of "uploading a file." The fundamentals below
— what actually happens to those bytes between your code and the
network, and back — are what let you reason about a stalled upload, a
corrupted download, or "why does this only work for small files" in a
way the library call itself never explains.

## From Bytes to Packets: What TCP Actually Does

- **IP** moves individual packets with no guarantees at all — a packet
  can arrive out of order, duplicated, or not arrive at all. On its own,
  it's not something you could reliably send a file over.
- **TCP** sits on top of IP and turns that unreliable packet delivery
  into what your application actually sees: a reliable, **ordered byte
  stream** — read from a TCP socket and you get the bytes in the exact
  order they were sent, with nothing missing, even though the packets
  carrying them may have taken different paths and arrived out of
  sequence.
- A large file isn't sent as one giant packet — it's broken into
  segments bounded by the network's **MTU** (typically ~1,500 bytes on
  Ethernet), each segment becomes one or more IP packets, and the
  **three-way handshake** (`SYN` → `SYN-ACK` → `ACK`) establishes the
  connection before any of this data starts flowing at all.

<svg viewBox="0 0 900 420" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Animated diagram of file segments arriving out of order over IP, then TCP reassembling them into the correct order before handing bytes to the application" style="width:100%;height:auto;max-width:900px;display:block;margin:0 auto;font-family:inherit;">
<rect x="0" y="0" width="900" height="420" fill="#ffffff" stroke="#d0d5dd" stroke-width="1"></rect>
<rect x="20" y="30" width="170" height="90" rx="8" fill="#eef1f5" stroke="#434d5c" stroke-width="2"></rect>
<text x="105" y="70" font-size="15" font-weight="600" text-anchor="middle" fill="#2b313b">Sender</text>
<text x="105" y="92" font-size="12" text-anchor="middle" fill="#5b6472">sends 1, 2, 3, 4 in order</text>
<rect x="690" y="150" width="190" height="130" rx="8" fill="#e8f7f0" stroke="#1f9d6b" stroke-width="2"></rect>
<text x="785" y="185" font-size="14" font-weight="600" text-anchor="middle" fill="#0f6b45">TCP Reassembly Buffer</text>
<text x="785" y="205" font-size="12" text-anchor="middle" fill="#3d9a73">holds out-of-order segments</text>
<text x="785" y="225" font-size="12" text-anchor="middle" fill="#3d9a73">until the gap is filled</text>
<circle r="16" fill="#eaf2fb" stroke="#2f6fb3" stroke-width="2" cx="105"><text x="105" y="5" font-size="13" text-anchor="middle" fill="#1d4a78">1</text><animate attributeName="cy" values="200;200;200;200" keyTimes="0;0.2;0.9;1" dur="14s" repeatCount="indefinite"></animate><animateMotion dur="14s" repeatCount="indefinite" keyPoints="0;0.2;1;1" keyTimes="0;0.2;0.35;1" calcMode="linear" path="M0,0 L680,-15"></animateMotion></circle>
<circle r="16" fill="#fdf3e3" stroke="#b5831f" stroke-width="2" cx="105"><text x="105" y="5" font-size="13" text-anchor="middle" fill="#7a5c14">2</text><animateMotion dur="14s" repeatCount="indefinite" keyPoints="0;0.2;1;1" keyTimes="0;0.2;0.62;1" calcMode="linear" path="M0,0 L680,25"></animateMotion></circle>
<circle r="16" fill="#fbe7e5" stroke="#c0392b" stroke-width="2" cx="105"><text x="105" y="5" font-size="13" text-anchor="middle" fill="#8e2d20">3</text><animateMotion dur="14s" repeatCount="indefinite" keyPoints="0;0.2;1;1" keyTimes="0;0.2;0.45;1" calcMode="linear" path="M0,0 L680,-5"></animateMotion></circle>
<circle r="16" fill="#f0e8f7" stroke="#7b4ea3" stroke-width="2" cx="105"><text x="105" y="5" font-size="13" text-anchor="middle" fill="#5a3878">4</text><animateMotion dur="14s" repeatCount="indefinite" keyPoints="0;0.2;1;1" keyTimes="0;0.2;0.68;1" calcMode="linear" path="M0,0 L680,35"></animateMotion></circle>
<text x="450" y="370" font-size="18" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.4;0.44;1" dur="14s" repeatCount="indefinite"></animate>Segments 1, 3, 2, 4 arrive in that order — IP never promised sequence.</text>
<text x="450" y="370" font-size="18" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.46;0.5;0.85;0.89;1" dur="14s" repeatCount="indefinite"></animate>TCP holds segment 3 until 2 arrives, then releases 1, 2, 3, 4 — in order.</text>
<text x="450" y="370" font-size="18" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.89;0.93;1" dur="14s" repeatCount="indefinite"></animate>The application only ever sees an in-order byte stream — this reordering is invisible above TCP.</text>
</svg>

!!! danger "A gap, not just reordering, is what actually stalls a transfer"

    Reordering alone is cheap to fix — TCP just holds the later segments
    in the reassembly buffer. A genuinely **lost** segment is what
    actually causes a visible stall: TCP has to detect the gap (via
    missing acknowledgment) and request retransmission before anything
    after that gap can be released to the application, even if every
    later segment already arrived. This is the real mechanism behind a
    download that "hangs" at some percentage for a few seconds before
    continuing — it isn't stuck, it's waiting on one retransmitted
    segment that everything after it depends on.

## Uploading: `multipart/form-data` vs. a Raw Body

Once the TCP connection exists, HTTP doesn't know or care that a file is
involved at all — it just sends bytes in a request body. "File upload"
is entirely a convention layered on top of plain bytes, and there are
two real shapes it takes:

`multipart/form-data`
:   What a browser sends from a `<form>` with a file input. The body is
    split into named **parts**, separated by a boundary string the
    `Content-Type` header declares — one part per form field, one part
    per file, each with its own small header block (`Content-Disposition`
    naming the field and original filename, `Content-Type` for that
    part's MIME type). This is the only reason a single request can
    carry both a file's bytes *and* ordinary form fields together.

`A raw/streamed body`
:   `PUT`/`POST` with the file as the **entire** request body
    (`Content-Type: application/octet-stream` or the file's real MIME
    type) — no boundaries, no parts, no extra form fields alongside it.
    Simpler and with less overhead than multipart, which is why most
    direct-to-storage upload APIs (presigned S3 URLs included) use this
    shape instead.

## Downloading: Content-Length, Chunked Transfer, and Range Requests

`Content-Length`
:   The normal case — the server already knows the full response size
    and declares it upfront, so the client knows exactly how many bytes
    to expect and when the body is complete.

`Transfer-Encoding: chunked`
:   Used when the server is generating a response as it goes and
    doesn't know the final size in advance (streaming search results,
    a dynamically assembled archive, server-sent events) — the body is
    sent as a series of length-prefixed chunks, ending with a
    zero-length chunk that marks completion, so the client still knows
    exactly when the body is done without a pre-declared total.

`Range` / `Accept-Ranges`
:   A server advertising `Accept-Ranges: bytes` supports fetching only
    **part** of a resource — a client sends `Range: bytes=1000-1999`,
    and the server replies `206 Partial Content` with just that slice
    (plus a `Content-Range` header stating which range and the total
    size). This single mechanism is what makes **resumable downloads**
    possible (a paused download just requests the remaining bytes, not
    the whole file again), what lets **video players seek** without
    downloading everything before the seek point, and what lets a
    download accelerator split one file across several parallel
    connections.

!!! success "The exam/interview-style signal"

    "Resume an interrupted download without starting over" or "let a
    user seek to the middle of a video without re-downloading it" →
    `Range` requests. "The server doesn't know the response size ahead
    of time" → `Transfer-Encoding: chunked`. "A form needs to submit a
    file alongside regular fields in one request" → `multipart/form-data`.

## Why This Means Code Should Stream, Not Buffer

Since the bytes are already arriving and leaving as a stream over TCP,
loading an entire multi-gigabyte file into memory before processing or
forwarding it throws away a property the network already gave you, for
nothing in return. This is the exact same buffering idea already
covered for local disk I/O in
[How File I/O Actually Works](../python/standard-library/pathlib-and-file-operations.md#how-file-io-actually-works) —
read/write/forward data in bounded chunks, not with an unbounded
`.read()`, and a server can handle a file larger than its own available
RAM, and a client can start acting on a download before it has even
finished arriving.
