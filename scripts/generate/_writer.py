"""Build RSS 2.0 XML from generated entries (stdlib only)."""

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import format_datetime

from generate import _history


def build_rss(feed: dict, entries: list[dict]) -> bytes:
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = feed["title"]
    ET.SubElement(channel, "link").text = feed["source"]
    ET.SubElement(channel, "description").text = feed["description"]
    ET.SubElement(channel, "language").text = "en"
    ET.SubElement(channel, "lastBuildDate").text = format_datetime(datetime.now(timezone.utc))

    for entry in entries:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = entry["title"]
        ET.SubElement(item, "link").text = entry["link"]
        guid = ET.SubElement(item, "guid", {"isPermaLink": "true"})
        guid.text = entry.get("guid") or entry["link"]
        ET.SubElement(item, "description").text = entry["description"]
        ET.SubElement(item, "pubDate").text = _history.to_rfc822(entry["date"])
        if entry.get("category"):
            ET.SubElement(item, "category").text = entry["category"]

    ET.indent(rss)
    return ET.tostring(rss, xml_declaration=True, encoding="UTF-8")
