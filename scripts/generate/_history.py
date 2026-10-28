"""History cache for type: generate feeds.

Websites only show their newest posts; the cache in cache/<feed>.json keeps
older entries so the published feed stays complete. Merging rules:

- entries are keyed by link; fresh extraction wins for content,
- a known link keeps its historical GUID (survives source URL migrations),
- output is sorted newest-first and capped at max_entries.
"""

import json
from datetime import datetime
from email.utils import format_datetime
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "cache"
CACHE_KEEP = 1000  # bound cache growth; far above any feed cap


def _decode(entry: dict) -> dict:
    return {**entry, "date": datetime.fromisoformat(entry["date"])}


def load(feed_name: str) -> dict[str, dict]:
    path = CACHE_DIR / f"{feed_name}.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    return {entry["link"]: _decode(entry) for entry in data.get("entries", [])}


def merge(feed_name: str, fresh: list[dict], max_entries: int) -> list[dict]:
    old = load(feed_name)
    merged = dict(old)
    for entry in fresh:
        link = entry["link"]
        known = old.get(link)
        if known:
            entry = {**entry, "guid": known.get("guid") or link}
        merged[link] = entry

    entries = sorted(merged.values(), key=lambda e: e["date"], reverse=True)
    persist = [{**e, "date": e["date"].isoformat()} for e in entries[:CACHE_KEEP]]
    CACHE_DIR.mkdir(exist_ok=True)
    (CACHE_DIR / f"{feed_name}.json").write_text(
        json.dumps({"entries": persist}, ensure_ascii=False, indent=1)
    )
    return entries[:max_entries]


def to_rfc822(dt) -> str:
    return format_datetime(dt)
