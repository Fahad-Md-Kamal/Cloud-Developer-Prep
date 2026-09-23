#!/usr/bin/env python3
"""Generate docs/nav-order.json: the site's pages in nav order.

Run before `zensical build` -- Zensical copies non-.md files under docs/
into the built site unchanged, so this becomes a static asset the
client-side PDF-export script (javascripts/download-pdf.js) can fetch
to know every page and the order to assemble them in.
"""
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOML = ROOT / "zensical.toml"
OUTPUT = ROOT / "docs" / "nav-order.json"


def flatten_nav(nav: list) -> list[dict]:
    """Walk the nav structure, returning ordered {title, path} entries."""
    pages = []
    for item in nav:
        for title, value in item.items():
            if isinstance(value, str):
                pages.append({"title": title, "path": value})
            elif isinstance(value, list):
                pages.extend(flatten_nav(value))
    return pages


def md_path_to_url(md_path: str) -> str:
    """docs/chapter-1.md -> chapter-1/  ; docs/index.md -> ./"""
    stem = md_path[:-3]  # strip .md
    if stem == "index":
        return "./"
    if stem.endswith("/index"):
        stem = stem[: -len("/index")]
    return f"{stem}/"


def main():
    config = tomllib.loads(TOML.read_text())
    pages = flatten_nav(config["project"]["nav"])
    for page in pages:
        page["url"] = md_path_to_url(page["path"])
        del page["path"]

    OUTPUT.write_text(json.dumps(pages, indent=2) + "\n")
    print(f"Wrote {len(pages)} pages to {OUTPUT}")


if __name__ == "__main__":
    main()
