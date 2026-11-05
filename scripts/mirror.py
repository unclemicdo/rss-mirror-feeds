"""Runner for type: mirror feeds — the source already publishes RSS/Atom."""

import feedlib


def run(feed: dict) -> tuple[str, str]:
    name = feed["name"]
    target = feedlib.FEEDS_DIR / f"{name}.xml"
    body = feedlib.fetch(feed["url"])
    info = feedlib.validate(body)

    old = target.read_bytes() if target.exists() else b""
    if feedlib.equivalent(body, old):
        # Same content modulo volatile build timestamps — keep published bytes
        # so no git commit is produced for a no-change refresh.
        return name, f"✅ unchanged, {info['entries']} entries, newest {info['newest']:%Y-%m-%d}"
    feedlib.atomic_write(target, body)
    return name, f"✅ updated, {info['entries']} entries, newest {info['newest']:%Y-%m-%d}"
