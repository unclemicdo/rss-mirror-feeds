"""Shared plumbing used by every feed type: fetch, validate, publish, report."""

import os
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent
FEEDS_DIR = ROOT / "feeds"

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


def canonical_form(body: bytes) -> str | None:
    """C14N-serialize an RSS/Atom document without volatile metadata.

    How:
    1. Parse; strip channel/feed-level build timestamps (lastBuildDate,
       channel pubDate, Atom feed updated) that are refreshed on every fetch.
    2. Keep everything else, including per-item dates and content.
    3. Return None for unparseable input so callers can fall back to a rewrite.
    """
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return None
    tag = local(root.tag).lower()
    if tag == "rss":
        channel = root.find("channel")
        if channel is None:
            return None
        for child in list(channel):
            if local(child.tag) in ("lastBuildDate", "pubDate"):
                channel.remove(child)
    elif tag == "feed":
        for child in list(root):
            if local(child.tag) == "updated":
                root.remove(child)
    else:
        return None
    return ET.canonicalize(ET.tostring(root, encoding="unicode"), strip_text=True)


def equivalent(new: bytes, old: bytes) -> bool:
    """True when the documents differ only in volatile build timestamps.

    Used to skip rewrites and git commits when a refresh brought no real
    change. Malformed previous bytes are never "equivalent" so a rewrite can
    repair them.
    """
    if not old:
        return False
    can_new = canonical_form(new)
    can_old = canonical_form(old)
    if can_new is None or can_old is None:
        return False
    return can_new == can_old


def atomic_write(target, body: bytes) -> None:
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
