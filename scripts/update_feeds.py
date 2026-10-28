#!/usr/bin/env python3
"""Mirror remote podcast RSS feeds into feeds/ for jsDelivr distribution.

Fetches each source, validates the document (RSS/Atom structure, non-empty
channel, unique GUIDs, parseable newest timestamp), and replaces the local
file atomically only when content changed — so git history only reflects real
updates and failed fetches keep the last known good XML.
"""

import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FEEDS_DIR = ROOT / "feeds"

SOURCES = {
    "feed_dwarkesh.xml": "https://apple.dwarkesh-podcast.workers.dev/feed.rss",
    "feed_yc_startup.xml": "https://anchor.fm/s/8c1524bc/podcast/rss",
}

TIMEOUT = 60
FUTURE_TOLERANCE = timedelta(hours=1)  # clock skew between source and runner
UA = "Mozilla/5.0 (compatible; rss-mirror/1.0; +https://github.com/unclemicdo/rss-mirror-feeds)"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_timestamp(text: str) -> datetime:
    text = text.strip()
    try:
        return parsedate_to_datetime(text)  # RFC 822 (RSS)
    except (TypeError, ValueError):
        return datetime.fromisoformat(text.replace("Z", "+00:00"))  # RFC 3339 (Atom)


def validate(body: bytes) -> dict:
    """Structural + content checks; returns summary info for CI reporting."""
    root = ET.fromstring(body)
    tag = local(root.tag).lower()
    if tag not in ("rss", "feed"):
        raise ValueError(f"unexpected root element <{root.tag}>")

    if tag == "rss":
        channel = root.find("channel")
        if channel is None:
            raise ValueError("rss root without <channel>")
        items = channel.findall("item")
    else:
        items = root.findall("entry")

    if not items:
        raise ValueError("feed has no entries")

    guids = set()
    newest = None
    for item in items:
        guid_el = next((el for el in item if local(el.tag) in ("guid", "id")), None)
        guid = (guid_el.text or "").strip() if guid_el is not None else ""
        if not guid:
            raise ValueError("entry without guid/id")
        if guid in guids:
            raise ValueError(f"duplicate guid {guid!r}")
        guids.add(guid)

        date_el = next((el for el in item if local(el.tag) in ("pubDate", "published", "updated")), None)
        if date_el is None or not (date_el.text or "").strip():
            raise ValueError(f"entry {guid!r} has no date")
        pub = parse_timestamp(date_el.text)
        if pub - datetime.now(timezone.utc) > FUTURE_TOLERANCE:
            raise ValueError(f"entry {guid!r} dated in the future: {pub}")

        if newest is None or pub > newest:
            newest = pub

    if newest is None:
        raise ValueError("no parseable timestamps")
    return {"entries": len(items), "newest": newest.astimezone(timezone.utc)}


def atomic_write(target: Path, body: bytes) -> None:
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_bytes(body)
    os.replace(tmp, target)


def write_summary(rows: list[tuple[str, str]]) -> None:
    """Append a markdown table to the GitHub job summary when running in CI."""
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    lines = ["| Feed | Result |", "|---|---|"]
    lines += [f"| {name} | {result} |" for name, result in rows]
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main() -> int:
    FEEDS_DIR.mkdir(exist_ok=True)
    rows: list[tuple[str, str]] = []
    failures = 0

    for name, url in SOURCES.items():
        target = FEEDS_DIR / name
        try:
            body = fetch(url)
            info = validate(body)
        except Exception as exc:  # noqa: BLE001 - CI reports every failure
            failures += 1
            rows.append((name, f"❌ FAILED: {exc}"))
            print(f"FAIL {name}: {exc}", file=sys.stderr)
            continue

        old = target.read_bytes() if target.exists() else b""
        if body != old:
            atomic_write(target, body)
            rows.append((name, f"✅ updated, {info['entries']} entries, newest {info['newest']:%Y-%m-%d}"))
            print(f"UPDATED {name} ({len(body)} bytes, {info['entries']} entries)")
        else:
            rows.append((name, f"✅ unchanged, {info['entries']} entries, newest {info['newest']:%Y-%m-%d}"))
            print(f"UNCHANGED {name}")

    write_summary(rows)
    if failures:
        print(f"{failures} feed(s) failed; keeping last known good XML", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
