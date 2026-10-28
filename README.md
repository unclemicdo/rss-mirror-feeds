# rss-mirror-feeds

Mirror podcast RSS feeds that are unreachable from the Miniflux server (blocked
or proxy-dependent sources) into this repo, served via jsDelivr CDN.

Feeds are refreshed every 7 hours by GitHub Actions; only valid RSS/Atom XML is
committed, and failed fetches keep the last known good file.

Subscribe via jsDelivr:

- Dwarkesh Podcast: `https://cdn.jsdelivr.net/gh/unclemicdo/rss-mirror-feeds@main/feeds/feed_dwarkesh.xml`
- Y Combinator Startup Podcast: `https://cdn.jsdelivr.net/gh/unclemicdo/rss-mirror-feeds@main/feeds/feed_yc_startup.xml`

Note: jsDelivr caches branch refs for up to ~12 hours.
