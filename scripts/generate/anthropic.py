"""Anthropic blog generator: extract articles from the Next.js listing pages.

anthropic.com has no RSS. Article listings are embedded in the page as Next.js
Flight transport chunks (self.__next_f.push). This module decodes those chunks
into JSON, reads initialPage.posts, and turns each post into a feed entry.

Extraction logic adapted from Olshansk/rss-feeds (MIT).
"""

import json
import re
from datetime import UTC, datetime
from urllib.parse import urljoin

import feedlib

FLIGHT_SCRIPT = re.compile(r"<script[^>]*>(self\.__next_f\.push\(.*?\);?)</script>", re.DOTALL)
FLIGHT_PUSH = re.compile(r"self\.__next_f\.push\((.*)\);?", re.DOTALL)


def _decode_flight_chunks(html: str) -> str:
    chunks = []
    for match in FLIGHT_SCRIPT.finditer(html):
        push = FLIGHT_PUSH.fullmatch(match.group(1))
        if not push:
            continue
        payload = json.loads(push.group(1))
        if len(payload) == 2 and payload[0] == 1 and isinstance(payload[1], str):
            chunks.append(payload[1])
    return "".join(chunks)


def parse_listing(html: str, team: str | None, allowed_types: tuple[str, ...]) -> list[dict]:
    """Extract article entries from a listing page's embedded Flight data.

    Strict on purpose: a site redesign must fail loudly, never publish an
    empty or half-parsed feed.
    """
    transport = _decode_flight_chunks(html)
    marker = re.search(r'"initialPage"\s*:\s*', transport)
    if marker is None:
        raise ValueError("listing page without initialPage data (site redesign?)")
    page, _ = json.JSONDecoder().raw_decode(transport[marker.end():])
    posts = page.get("posts")
    if not isinstance(posts, list) or not posts:
        raise ValueError("Anthropic listing contains no posts")

    entries = []
    for post in posts:
        if team is not None and team not in {t["slug"] for t in post.get("cardTeams", [])}:
            raise ValueError(f"article does not belong to team {team!r}")
        title = (post.get("title") or "").strip()
        slug = (post.get("slug") or {}).get("current")
        article_type = post.get("articleType")
        if not title or not (slug or post.get("linkedUrl")) or article_type not in allowed_types:
            raise ValueError(f"article missing valid title/slug/type: {title!r}")
        link = urljoin("https://www.anthropic.com", post.get("linkedUrl") or f"/{article_type}/{slug}")
        entries.append(
            {
                "title": title,
                "link": link,
                "description": ((post.get("summary") or "").strip() or title),
                "date": datetime.strptime(post["publishedOn"], "%Y-%m-%d").replace(tzinfo=UTC),
                "category": "Engineering" if team == "engineering" else article_type.title(),
            }
        )
    return entries


def run(feed: dict) -> list[dict]:
    html = feedlib.fetch(feed["source"]).decode("utf-8")
    return parse_listing(html, feed.get("team"), tuple(feed["allowed_types"]))
