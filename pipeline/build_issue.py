"""
Build orchestrator that generates static feeds (RSS, JSON) and exported data bundles.
Follows Section 5.5 and Section 5.6 (Delivery & Archive).
"""

import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
import datetime
from core.db import Database
from core.ledger import LedgerEngine


def build_static_artifacts(db_path: str = "brief.sqlite3", output_dir: str = "public"):
    db = Database(db_path)
    latest_issue = db.get_latest_issue()
    if not latest_issue:
        print("No issue found in database.")
        return

    predictions = db.get_all_predictions()
    ledger_stats = LedgerEngine.calculate_statistics(predictions)

    # 1. Generate JSON Feed
    feed_data = {
        "version": "https://jsonfeed.org/version/1.1",
        "title": "Pith · Signal Intelligence",
        "home_page_url": "https://pith.news",
        "feed_url": "https://pith.news/feed.json",
        "description": "Pith filters tech noise down to events that alter architectures, margins, or moats.",
        "issue": latest_issue.to_dict(),
        "ledger": {
            "stats": ledger_stats,
            "predictions": [p.__dict__ for p in predictions]
        }
    }

    with open(f"{output_dir}/feed.json", "w", encoding="utf-8") as f:
        json.dump(feed_data, f, indent=2)

    # 2. Generate RSS 2.0 XML
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "Pith · Signal Intelligence"
    ET.SubElement(channel, "link").text = "https://pith.news"
    ET.SubElement(channel, "description").text = "Filtered tech intelligence: AI & Developer Infrastructure."
    ET.SubElement(channel, "language").text = "en-us"
    ET.SubElement(channel, "lastBuildDate").text = datetime.datetime.now(datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    for card in latest_issue.cards:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = f"[{card.signal_level} Signal] {card.headline}"
        ET.SubElement(item, "link").text = f"https://pith.news/#{card.id}"
        ET.SubElement(item, "guid").text = card.id
        ET.SubElement(item, "pubDate").text = datetime.datetime.now(datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
        desc_text = f"{card.what_happened}\n\nWhy it matters: {card.why_it_matters}\n\nAction ({card.action_type}): {card.action_text}"
        ET.SubElement(item, "description").text = desc_text

    xml_str = minidom.parseString(ET.tostring(rss)).toprettyxml(indent="  ")
    with open(f"{output_dir}/rss.xml", "w", encoding="utf-8") as f:
        f.write(xml_str)

    # 3. Generate Static Plain-Text ANSI CLI Briefs for curl
    from core.cli_format import render_cli_brief
    for role in ["developer", "founder", "investor", "everyday"]:
        filename = "dev" if role == "developer" else ("plain" if role == "everyday" else role)
        cli_content = render_cli_brief(latest_issue, role=role)
        with open(f"{output_dir}/{filename}", "w", encoding="utf-8") as f:
            f.write(cli_content)
        with open(f"{output_dir}/{filename}.txt", "w", encoding="utf-8") as f:
            f.write(cli_content)

    print(f"Generated {output_dir}/feed.json, {output_dir}/rss.xml, and static CLI endpoints successfully.")


if __name__ == "__main__":
    build_static_artifacts()
