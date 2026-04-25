#!/usr/bin/env python3
"""
RSS news fetcher — pulls free RSS feeds listed in news_sources.yaml, dedupes by URL hash,
appends to lab/news/YYYY-MM-DD.jsonl (UTC date).

Each JSONL record:
  {ts, source, category, title, url, summary, hash}

Idempotent: running multiple times in a day only adds new unseen items.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import feedparser
except ImportError:
    print("feedparser not installed. run: pip3 install feedparser pyyaml", file=sys.stderr)
    sys.exit(1)

try:
    import yaml
except ImportError:
    print("pyyaml not installed. run: pip3 install pyyaml", file=sys.stderr)
    sys.exit(1)


ROOT = Path(__file__).resolve().parent.parent.parent  # repo root
SOURCES_FILE = Path(__file__).resolve().parent / "news_sources.yaml"
NEWS_DIR = ROOT / "lab" / "news"


def load_feeds() -> list[dict]:
    with open(SOURCES_FILE) as f:
        data = yaml.safe_load(f)
    return data.get("feeds", [])


def load_existing_hashes(today_file: Path) -> set[str]:
    if not today_file.exists():
        return set()
    hashes = set()
    for line in today_file.read_text().splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
            hashes.add(rec.get("hash", ""))
        except json.JSONDecodeError:
            continue
    return hashes


def parse_entry(entry, feed_meta: dict) -> dict | None:
    url = entry.get("link") or entry.get("id")
    if not url:
        return None
    title = (entry.get("title") or "").strip()
    if not title:
        return None
    # Prefer 'published_parsed', fallback to 'updated_parsed', fallback to now
    struct_time = entry.get("published_parsed") or entry.get("updated_parsed")
    if struct_time:
        ts = datetime(*struct_time[:6], tzinfo=timezone.utc)
    else:
        ts = datetime.now(timezone.utc)

    summary = (entry.get("summary") or entry.get("description") or "").strip()
    # Strip simple HTML tags crudely
    if "<" in summary:
        import re
        summary = re.sub(r"<[^>]+>", "", summary)
    if len(summary) > 500:
        summary = summary[:497] + "..."

    url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]

    return {
        "ts": ts.isoformat(),
        "source": feed_meta["source"],
        "category": feed_meta["category"],
        "title": title,
        "url": url,
        "summary": summary,
        "hash": url_hash,
    }


def main() -> int:
    NEWS_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_file = NEWS_DIR / f"{today}.jsonl"
    seen = load_existing_hashes(out_file)

    feeds = load_feeds()
    total_new = 0
    per_source: dict[str, int] = {}
    failures: list[tuple[str, str]] = []

    for feed_meta in feeds:
        url = feed_meta["url"]
        source = feed_meta["source"]
        try:
            parsed = feedparser.parse(url)
            if parsed.bozo and not parsed.entries:
                failures.append((source, str(parsed.bozo_exception)[:120]))
                continue
        except Exception as e:  # noqa: BLE001
            failures.append((source, str(e)[:120]))
            continue

        new_count = 0
        with open(out_file, "a") as f:
            for entry in parsed.entries:
                rec = parse_entry(entry, feed_meta)
                if rec is None:
                    continue
                if rec["hash"] in seen:
                    continue
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                seen.add(rec["hash"])
                new_count += 1
        per_source[source] = new_count
        total_new += new_count

    # Stderr summary (stdout reserved for potential future JSON output)
    print(f"[fetch_news] wrote {total_new} new items to {out_file}", file=sys.stderr)
    for src, n in sorted(per_source.items(), key=lambda kv: -kv[1]):
        if n:
            print(f"  + {src}: {n}", file=sys.stderr)
    if failures:
        print(f"[fetch_news] {len(failures)} source(s) failed:", file=sys.stderr)
        for src, err in failures:
            print(f"  ! {src}: {err}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
