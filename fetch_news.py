#!/usr/bin/env python3
"""
Hourly tech / AI / innovation news digest -> phone push notification.
"""

import os
import sys
import time
from datetime import datetime, timedelta, timezone

import feedparser
import requests

NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "changeme-topic")
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh")
LOOKBACK_MINUTES = int(os.environ.get("LOOKBACK_MINUTES", "75"))
MAX_ITEMS = int(os.environ.get("MAX_ITEMS", "8"))

FEEDS = [
    ("TechCrunch", "https://techcrunch.com/feed/"),
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("The Verge", "https://www.theverge.com/rss/index.xml"),
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
    ("MIT Technology Review", "https://www.technologyreview.com/feed/"),
    ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/"),
    ("Wired", "https://www.wired.com/feed/rss"),
    ("Hacker News (front page)", "https://hnrss.org/frontpage"),
]


def entry_time(entry):
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc)
    return None


def collect_recent_items():
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=LOOKBACK_MINUTES)
    items = []
    for source, url in FEEDS:
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            print(f"[warn] failed to parse {source} ({url}): {e}", file=sys.stderr)
            continue
        for entry in feed.entries:
            ts = entry_time(entry)
            if ts and ts >= cutoff:
                items.append({
                    "source": source,
                    "title": entry.get("title", "Untitled"),
                    "link": entry.get("link", ""),
                    "time": ts,
                })
    items.sort(key=lambda i: i["time"], reverse=True)
    seen_links = set()
    deduped = []
    for it in items:
        if it["link"] in seen_links:
            continue
        seen_links.add(it["link"])
        deduped.append(it)
    return deduped[:MAX_ITEMS]


def send_notification(items):
    if not items:
        print("No new items this run - nothing sent.")
        return
    lines = [f"{i + 1}. [{it['title']}]({it['link']}) — {it['source']}" for i, it in enumerate(items)]
    body = "\n".join(lines)
    title = f"Tech/AI News — {datetime.now(timezone.utc).strftime('%H:%M UTC')}"
    resp = requests.post(
        f"{NTFY_SERVER}/{NTFY_TOPIC}",
        data=body.encode("utf-8"),
        headers={"Title": title, "Markdown": "yes", "Priority": "default", "Tags": "robot"},
        timeout=15,
    )
    resp.raise_for_status()
    print(f"Sent {len(items)} item(s) to ntfy topic '{NTFY_TOPIC}'.")


if __name__ == "__main__":
    recent = collect_recent_items()
    send_notification(recent)
