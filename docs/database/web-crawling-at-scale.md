---
title: "Web Crawling at Scale: Scrapy, Selenium & Playwright"
---

# Web Crawling at Scale: Scrapy, Selenium & Playwright

Knowing Scrapy's settings or Playwright's API is the tool-usage version
of web crawling. The fundamentals underneath — why some pages need a
real browser and others don't, why crawling is fundamentally an
I/O-concurrency problem, and what a site is actually detecting when it
blocks a bot — are what let a crawler keep working when a site changes
something the tool's defaults never covered.

## Why Some Pages Need a Real Browser at All

A plain HTTP `GET` (see
[how a browser actually fetches a page](../architecture/how-the-internet-moves-files.md))
returns whatever HTML the server sent — for a traditional server-rendered
page, that's the full content. For a modern single-page application, the
server often sends back a nearly empty HTML shell plus a bundle of
JavaScript; the actual content gets built into the DOM by that
JavaScript running *in a browser*, after the initial response. A raw
`GET` request, or a simple HTML parser pointed at that response, never
sees the real content at all — there's nothing to parse yet.

This is the entire reason Selenium and Playwright exist: they drive a
real browser engine, so the JavaScript actually executes and the DOM
actually finishes building, before anything tries to extract data from
it. A library like BeautifulSoup or `requests` alone has no way to run
JavaScript — it only ever sees the raw response bytes.

## Selenium vs. Playwright: the Actual Protocol Difference

**Answer:**

- **Selenium** drives a browser through the **WebDriver protocol** — a
  standardized, cross-browser JSON-over-HTTP wire protocol. Every
  command (click this, read that element's text) is its own HTTP
  request/response round trip to a separate driver process sitting
  between your code and the browser.
- **Playwright** connects directly to the browser's own automation
  protocol (Chromium's DevTools Protocol, and equivalents for
  Firefox/WebKit) over a single persistent WebSocket connection — no
  intermediate driver process, and no per-command HTTP round trip.
- The practical consequence: Playwright is measurably faster for
  command-heavy automation, and it has native, built-in ways to wait for
  "network idle" or a specific element's actual readiness, instead of
  the manual `sleep()`-and-hope or polling loops that was long the
  normal pattern in Selenium scripts.
- Both ultimately solve the same problem (drive a real browser); the
  protocol difference is why one framework feels faster and more
  reliable at scale than the other, not a difference in what's possible
  with either.

## Why Scrapy Is Built on an Async Event Loop, Not Sequential Requests

**Answer:**

- Crawling is almost entirely **I/O-bound** — a crawler spends the vast
  majority of its time waiting on network responses, not doing CPU work.
- Scrapy is built on Twisted, an asynchronous networking framework that
  predates `asyncio` but solves the identical problem: one event loop
  can have hundreds of requests in flight at once, switching to whichever
  response arrives next instead of blocking on one request at a time.
- This is the same underlying reasoning as
  [AsyncIO Internals](../python/asyncio-internals.md) and
  [Choosing a Concurrency Model](../python/choosing-a-concurrency-model.md) —
  I/O-bound work is exactly where concurrency multiplies real throughput,
  because the bottleneck is waiting, not computing.
- This is also why a naive sequential crawler (one `requests.get()` at a
  time, in a loop) is dramatically slower than Scrapy at any real scale —
  it's paying the full network round-trip latency of every single request
  serially, with no overlap at all.

## What a Site Actually Detects When It Blocks a Bot

**Answer:**

- Rotating the `User-Agent` header alone fools almost nothing today —
  real anti-bot systems fingerprint far more than one header.
- **TLS handshake fingerprinting (JA3)** — the specific order and set of
  cipher suites/extensions a client offers during the TLS handshake
  differs measurably between a real browser and most HTTP libraries,
  identifiable before a single byte of HTTP is even exchanged.
- **HTTP header order and casing** — real browsers send headers in a
  specific, consistent order; a scripted client's library often sends
  them in a different order or with different casing, a detectable
  signature independent of header *content*.
- **Automation flags in the JS environment** — a real browser driven by
  WebDriver historically exposed `navigator.webdriver = true` and other
  subtle differences in the JS runtime (missing browser plugins,
  inconsistent screen/timing properties) that a page's own JavaScript
  can check for before deciding whether to serve real content.
- **Request timing and pattern** — a human pauses, scrolls, and moves a
  mouse with real variance; a scripted crawler hitting pages at
  machine-precise intervals is a statistical signal on its own,
  independent of anything in a single request.
- The honest takeaway: there's no single setting that defeats detection
  — it's the same "defense in depth, no silver bullet" shape as
  [prompt injection defense](../ai-llm/prompt-engineering.md#4-your-application-takes-untrusted-user-input-and-feeds-it-into-a-prompt-that-also-has-system-instructions-and-possibly-tool-access-whats-the-actual-attack-and-how-do-you-defend-against-it)
  elsewhere on this site — mitigations reduce detection, they don't
  eliminate it.

## Crawling Politely, and When Scale Needs More Than One Machine

**Answer:**

- `robots.txt` isn't enforced by the browser or the network — it's a
  convention a crawler has to actually choose to read and respect; both
  Scrapy and most serious crawling setups parse and honor it by default.
- Per-domain rate limiting matters independently of being polite — the
  same [token-bucket reasoning](../distributed-systems/rate-limiting-strategies.md#1-compare-token-bucket-and-sliding-window-rate-limiting-which-would-you-pick-and-why)
  covered for API gateways applies directly here: cap concurrent
  requests and request rate *per target domain*, not just globally,
  since a target site's own capacity is what you're actually bound by.
- A single machine's bandwidth, CPU, and IP reputation all become real
  ceilings at genuine scale — coordinating many workers, deduplicating a
  shared URL frontier across them, and surviving individual worker
  failures is a distinct problem from fetching any one page, covered
  next in
  [Distributed Crawling Architecture](distributed-crawling-architecture.md).

| Pros | Cons / Trade-offs |
|---|---|
| Playwright's direct protocol connection is faster and more reliable than Selenium's WebDriver round trips | Still has to actually execute JS and wait for rendering — slower per page than a plain HTTP request |
| Scrapy's async event loop gets far higher throughput than a sequential crawler | Harder to debug than sequential code — many requests genuinely in flight at once |
| Respecting robots.txt and per-domain rate limits avoids getting IP-banned outright | Real anti-bot detection has no single fix — mitigations reduce, not eliminate, detection risk |

---

## Code Samples

No dedicated code samples for this page.
