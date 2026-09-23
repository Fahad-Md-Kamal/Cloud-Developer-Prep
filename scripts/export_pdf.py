#!/usr/bin/env python3
"""Export the whole Zensical site to one merged PDF, in nav order.

Usage (from the repo root):
    zensical build --clean
    python3 scripts/export_pdf.py

Requires: google-chrome (headless print-to-pdf) and pdfunite (poppler-utils).
"""
import http.server
import socketserver
import subprocess
import threading
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOML = ROOT / "zensical.toml"
SITE = ROOT / "site"
OUTPUT = ROOT / "Cloud-Developer-Prep.pdf"
PORT = 8791


def flatten_nav(nav: list) -> list[str]:
    """Walk the nav structure, returning an ordered list of .md paths."""
    paths = []
    for item in nav:
        for _title, value in item.items():
            if isinstance(value, str):
                paths.append(value)
            elif isinstance(value, list):
                paths.extend(flatten_nav(value))
    return paths


def md_path_to_url(md_path: str) -> str:
    """docs/chapter-1.md -> /chapter-1/  ; docs/index.md -> /"""
    stem = md_path[:-3]  # strip .md
    if stem == "index":
        return "/"
    if stem.endswith("/index"):
        stem = stem[: -len("/index")]
    return f"/{stem}/"


def main():
    if not SITE.is_dir():
        raise SystemExit("site/ not found -- run `zensical build --clean` first")

    config = tomllib.loads(TOML.read_text())
    md_paths = flatten_nav(config["project"]["nav"])
    print(f"{len(md_paths)} pages found in nav order")

    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(
        *a, directory=str(SITE), **kw
    )
    httpd = socketserver.TCPServer(("", PORT), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    tmp_dir = ROOT / ".pdf-build"
    tmp_dir.mkdir(exist_ok=True)
    try:
        pdf_files = []
        for i, md_path in enumerate(md_paths):
            url = f"http://localhost:{PORT}{md_path_to_url(md_path)}"
            out = tmp_dir / f"{i:03d}.pdf"
            subprocess.run(
                [
                    "google-chrome",
                    "--headless",
                    "--disable-gpu",
                    "--no-sandbox",
                    "--print-to-pdf-no-header",
                    f"--print-to-pdf={out}",
                    "--virtual-time-budget=5000",
                    url,
                ],
                check=True,
                capture_output=True,
            )
            pdf_files.append(str(out))
            print(f"[{i + 1}/{len(md_paths)}] {md_path}")

        subprocess.run(["pdfunite", *pdf_files, str(OUTPUT)], check=True)
    finally:
        httpd.shutdown()
        for f in tmp_dir.glob("*.pdf"):
            f.unlink()
        tmp_dir.rmdir()

    print(f"\nCombined PDF: {OUTPUT} ({OUTPUT.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
