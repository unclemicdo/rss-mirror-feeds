"""Equivalence tests for the normalized publish comparison in feedlib."""

import unittest

from scripts.feedlib import canonical_form, equivalent

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Example</title>
    <lastBuildDate>{stamp}</lastBuildDate>
    <pubDate>{stamp}</pubDate>
    <item>
      <title>One</title>
      <link>https://example.com/one</link>
      <guid>https://example.com/one</guid>
      <pubDate>Thu, 06 Nov 2025 10:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""

RSS_ADDED_ITEM = RSS.format(stamp="Fri, 07 Nov 2025 11:00:00 GMT").replace(
    "    </item>\n  </channel>",
    """    </item>
    <item>
      <title>Two</title>
      <link>https://example.com/two</link>
      <guid>https://example.com/two</guid>
      <pubDate>Fri, 07 Nov 2025 12:00:00 GMT</pubDate>
    </item>
  </channel>""",
)

ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Example</title>
  <updated>{stamp}</updated>
  <entry>
    <title>One</title>
    <link href="https://example.com/one"/>
    <id>https://example.com/one</id>
    <updated>2025-11-06T10:00:00Z</updated>
  </entry>
</feed>
"""


class EquivalentTest(unittest.TestCase):
    def test_build_timestamp_only_change_is_equivalent(self):
        old = RSS.format(stamp="Thu, 06 Nov 2025 11:00:00 GMT").encode()
        new = RSS.format(stamp="Fri, 07 Nov 2025 11:00:00 GMT").encode()
        self.assertTrue(equivalent(new, old))

    def test_new_item_is_not_equivalent(self):
        old = RSS.format(stamp="Thu, 06 Nov 2025 11:00:00 GMT").encode()
        new = RSS_ADDED_ITEM.encode()
        self.assertFalse(equivalent(new, old))

    def test_indentation_only_change_is_equivalent(self):
        old = RSS.format(
            stamp="Thu, 06 Nov 2025 11:00:00 GMT"
        ).encode()
        new = (
            RSS.format(stamp="Fri, 07 Nov 2025 11:00:00 GMT")
            .replace("  <channel>", "      <channel>")
            .replace("    <item>", "        <item>")
            .encode()
        )
        self.assertTrue(equivalent(new, old))

    def test_atom_feed_updated_only_change_is_equivalent(self):
        old = ATOM.format(stamp="2025-11-06T11:00:00Z").encode()
        new = ATOM.format(stamp="2025-11-07T11:00:00Z").encode()
        self.assertTrue(equivalent(new, old))

    def test_entry_content_change_is_not_equivalent(self):
        unchanged = ATOM.format(stamp="2025-11-06T11:00:00Z")
        changed = unchanged.replace(
            "<updated>2025-11-06T10:00:00Z</updated>",
            "<updated>2025-11-08T10:00:00Z</updated>",
        ).encode()
        self.assertFalse(equivalent(changed, unchanged.encode()))

    def test_no_previous_file_is_never_equivalent(self):
        new = RSS.format(stamp="Fri, 07 Nov 2025 11:00:00 GMT").encode()
        self.assertFalse(equivalent(new, b""))
        self.assertFalse(equivalent(new, b""))

    def test_malformed_previous_file_is_never_equivalent(self):
        new = RSS.format(stamp="Fri, 07 Nov 2025 11:00:00 GMT").encode()
        self.assertFalse(equivalent(new, b"<rss><channel>truncated"))

    def test_canonical_form_rejects_garbage(self):
        self.assertIsNone(canonical_form(b"not xml"))
        self.assertIsNone(canonical_form(b"<html><body></body></html>"))
        self.assertIsNone(canonical_form(b"<rss><channel><item><title>x</title>"))


if __name__ == "__main__":
    unittest.main()