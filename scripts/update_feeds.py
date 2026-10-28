#!/usr/bin/env python3
"""Refresh all enabled feeds from the registry.

Dispatches per-feed by type (mirror / generate), validates every output with
the same rules, publishes atomically, and reports per-feed results to the CI
job summary. A failing feed never prevents other feeds from updating, but the
run itself stays failed so the broken source remains visible.
"""

import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import feedlib
from feeds_registry import FEEDS
from generate import _writer, _history


def run_generate(feed: dict) -> list[dict]:
    module = importlib.import_module(f"generate.{feed['generator']}")
    fresh = module.run(feed)
    if not fresh:
        raise ValueError("generator extracted no entries")
    return _history.merge(feed["name"], fresh, feed["max_entries"])


def process(feed: dict) -> tuple[str, str]:
    name = feed["name"]
    if not feed.get("enabled", True):
        return (name, "⏸ disabled, keeping last known good XML")

    if feed["type"] == "mirror":
        import mirror

        return mirror.run(feed)

    entries = run_generate(feed)
    body = _writer.build_rss(feed, entries)
    info = feedlib.validate(body)  # generated output passes the same checks

    target = feedlib.FEEDS_DIR / f"{name}.xml"
    old = target.read_bytes() if target.exists() else b""
    if body == old:
        return (name, f"✅ unchanged, {info['entries']} entries, newest {info['newest']:%Y-%m-%d}")
    feedlib.atomic_write(target, body)
    return (name, f"✅ updated, {info['entries']} entries, newest {info['newest']:%Y-%m-%d}")


def main() -> int:
    feedlib.FEEDS_DIR.mkdir(exist_ok=True)
    rows: list[tuple[str, str]] = []
    failures = 0

    for feed in FEEDS:
        try:
            rows.append(process(feed))
            print(f"OK {feed['name']}")
        except Exception as exc:  # noqa: BLE001 - CI reports every failure
            failures += 1
            rows.append((feed["name"], f"❌ FAILED: {exc}"))
            print(f"FAIL {feed['name']}: {exc}", file=sys.stderr)

    feedlib.write_summary(rows)
    if failures:
        print(f"{failures} feed(s) failed; keeping last known good XML", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
