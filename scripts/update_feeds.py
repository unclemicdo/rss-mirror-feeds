#!/usr/bin/env python3
"""Mirror remote podcast RSS feeds into feeds/ for jsDelivr distribution.

Fetches each source, validates the XML parses as RSS/Atom, and rewrites the
local file only when content changed (so git history only reflects real updates).
"""

import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FEEDS_DIR = ROOT / "feeds"

SOURCES = {
    "feed_dwarkesh.xml": "https://apple.dwarkesh-podcast.workers.dev/feed.rss",
    "feed_yc_startup.xml": "https://anchor.fm/s/8c1524bc/podcast/rss",
}

TIMEOUT = 60
UA = "Mozilla/5.0 (compatible; rss-mirror/1.0; +https://github.com/unclemicdo/rss-mirror-feeds)"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def validate(body: bytes) -> None:
    root = ET.fromstring(body)
    tag = root.tag.rsplit("}", 1)[-1].lower()
    if tag not in ("rss", "feed"):
        raise ValueError(f"unexpected root element <{root.tag}>")


def main() -> int:
    FEEDS_DIR.mkdir(exist_ok=True)
    failures = []
    for name, url in SOURCES.items():
        target = FEEDS_DIR / name
        try:
            body = fetch(url)
            validate(body)
        except Exception as exc:  # noqa: BLE001 - report every failure in CI
            failures.append(f"{name}: {exc}")
            print(f"FAIL {name}: {exc}", file=sys.stderr)
            continue

        old = target.read_bytes() if target.exists() else b""
        if body != old:
            target.write_bytes(body)
            print(f"UPDATED {name} ({len(body)} bytes)")
        else:
            print(f"UNCHANGED {name}")

    if failures:
        print(f"{len(failures)} feed(s) failed; keeping last known good XML", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
