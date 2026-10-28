"""Feed registry: which feeds exist, how they are refreshed, and their metadata.

Two types are supported:

- mirror:   the source already publishes RSS/Atom; we mirror its bytes.
- generate: the site has no RSS; a generator in scripts/generate/ extracts
            entries from the page and builds RSS, merged with cached history.

Kept as a Python module (not YAML) so the registry stays dependency-free and
commentable.
"""

FEEDS = [
    {
        "name": "feed_dwarkesh",
        "type": "mirror",
        "url": "https://apple.dwarkesh-podcast.workers.dev/feed.rss",
        "enabled": True,
    },
    {
        "name": "feed_yc_startup",
        "type": "mirror",
        "url": "https://anchor.fm/s/8c1524bc/podcast/rss",
        "enabled": True,
    },
    {
        "name": "feed_anthropic_engineering",
        "type": "generate",
        "generator": "anthropic",
        "source": "https://www.anthropic.com/engineering",
        "team": "engineering",
        "allowed_types": ("research", "news"),
        "title": "Anthropic Engineering Blog",
        "description": "Latest engineering articles and insights from Anthropic's engineering team",
        "max_entries": 100,
        "enabled": True,
    },
    {
        "name": "feed_anthropic_news",
        "type": "generate",
        "generator": "anthropic",
        "source": "https://www.anthropic.com/news",
        "team": None,
        "allowed_types": ("news",),
        "title": "Anthropic News",
        "description": "News and announcements from Anthropic",
        "max_entries": 100,
        "enabled": True,
    },
]
