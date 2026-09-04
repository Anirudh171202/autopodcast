"""Episode index bookkeeping + RSS/podcast feed generation.

`state/episodes_index.json` is the source of truth for what's live; feed.xml
is fully regenerated from it every run rather than edited incrementally, so
it can never drift out of sync with what's actually in docs/episodes/.
"""

import html
import json
import os
from datetime import datetime, timedelta, timezone

from feedgen.feed import FeedGenerator

from . import config


def load_index() -> list[dict]:
    if config.INDEX_PATH.exists():
        with open(config.INDEX_PATH) as f:
            return json.load(f)
    return []


def save_index(index: list[dict]) -> None:
    config.STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.INDEX_PATH, "w") as f:
        json.dump(index, f, indent=2)


def prune_old_episodes(index: list[dict], retention_days: int) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    kept, removed = [], []
    for ep in index:
        if datetime.fromisoformat(ep["published"]) >= cutoff:
            kept.append(ep)
        else:
            removed.append(ep)
    for ep in removed:
        mp3_path = config.DOCS_DIR / ep["file"]
        if mp3_path.exists():
            mp3_path.unlink()
    return kept


def add_episode(
    index: list[dict],
    *,
    date_str: str,
    title: str,
    description: str,
    file_rel_path: str,
    duration_seconds: float,
    size_bytes: int,
) -> list[dict]:
    hours, remainder = divmod(int(duration_seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    entry = {
        "date": date_str,
        "title": title,
        "description": description,
        "file": file_rel_path,
        "published": datetime.now(timezone.utc).isoformat(),
        "duration_hms": f"{hours}:{minutes:02d}:{seconds:02d}",
        "size_bytes": size_bytes,
    }
    # Replace any existing entry for the same date (e.g. a manual re-run).
    index = [ep for ep in index if ep["date"] != date_str]
    index.append(entry)
    return index


def build_feed(index: list[dict], cfg: dict) -> None:
    fg = FeedGenerator()
    fg.load_extension("podcast")
    fg.title(cfg["podcast_title"])
    fg.link(href=cfg["feed_base_url"], rel="alternate")
    fg.description(cfg["podcast_description"])
    fg.language("en")
    fg.podcast.itunes_category("News")
    fg.podcast.itunes_explicit("no")

    for ep in sorted(index, key=lambda e: e["published"], reverse=True):
        fe = fg.add_entry()
        fe.id(ep["file"])
        fe.title(ep["title"])
        fe.description(ep["description"])
        fe.enclosure(f"{cfg['feed_base_url']}/{ep['file']}", str(ep["size_bytes"]), "audio/mpeg")
        fe.pubDate(ep["published"])
        fe.podcast.itunes_duration(ep["duration_hms"])

    config.DOCS_DIR.mkdir(parents=True, exist_ok=True)
    fg.rss_file(str(config.FEED_PATH))


def build_index_html(index: list[dict], cfg: dict) -> None:
    """A tiny landing page so the Pages root isn't a dead 404 — the feed URL
    itself is what actually matters to a podcast app."""
    rows = "\n".join(
        f"<li><strong>{html.escape(ep['title'])}</strong> "
        f"({ep['duration_hms']}) — "
        f"<a href=\"{html.escape(ep['file'])}\">listen</a></li>"
        for ep in sorted(index, key=lambda e: e["published"], reverse=True)
    )
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(cfg['podcast_title'])}</title>
</head>
<body style="font-family: sans-serif; max-width: 40em; margin: 2em auto; padding: 0 1em;">
<h1>{html.escape(cfg['podcast_title'])}</h1>
<p>{html.escape(cfg['podcast_description'])}</p>
<p>Subscribe in your podcast app with this feed URL:
<code>{html.escape(cfg['feed_base_url'])}/feed.xml</code></p>
<h2>Episodes</h2>
<ul>
{rows or "<li>No episodes yet.</li>"}
</ul>
</body>
</html>
"""
    config.DOCS_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.DOCS_DIR / "index.html", "w") as f:
        f.write(page)
