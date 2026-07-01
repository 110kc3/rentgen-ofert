"""Persistent gallery-hash cache: skip re-fetching photos we've already hashed.

`photomatch` fetches each ambiguous listing's detail page plus a few gallery
images and computes a dHash per image - by far the slowest, most rate-limited
part of a run. A listing's photos never change, so we key the result by listing
URL and reuse it on later runs.

The cache lives in ``cache/phash_cache.json`` (committed, so the GitHub Actions
job reuses it run-to-run) and self-prunes URLs not seen for ``MAX_AGE_DAYS`` so
it can't grow without bound:

    {"version": 1, "entries": {url: {"hashes": ["<int>", ...], "seen": "YYYY-MM-DD",
                                     "urls": ["https://...", ...]}}}

dHashes are 256-bit ints; they're stored as decimal strings so the JSON stays
portable, and parsed back to int on read. "urls" (the gallery image URLs the
hashes came from) was added later and is optional — old entries lack it.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib

VERSION = 1
MAX_AGE_DAYS = 21  # drop a URL we haven't seen in this many days


def load(path) -> dict:
    try:
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("entries"), dict):
            return data
    except Exception:
        pass
    return {"version": VERSION, "entries": {}}


def save(path, cache) -> None:
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cache, ensure_ascii=False, indent=0), encoding="utf-8")


def get(cache, url):
    """Cached gallery hashes (list[int]) for ``url``, or None if not cached."""
    entry = cache.get("entries", {}).get(url)
    if not entry:
        return None
    try:
        return [int(h) for h in entry.get("hashes", [])]
    except (TypeError, ValueError):
        return None


def get_urls(cache, url):
    """Cached gallery image URLs for ``url`` (may be [] for old entries)."""
    entry = cache.get("entries", {}).get(url)
    return list(entry.get("urls") or []) if entry else []


def put(cache, url, hashes, today: str, image_urls=None) -> None:
    """Store (non-empty) gallery hashes for ``url``, stamped as seen ``today``."""
    if not url or not hashes:
        return
    entry = {"hashes": [str(int(h)) for h in hashes], "seen": today}
    if image_urls:
        entry["urls"] = list(image_urls)
    cache.setdefault("entries", {})[url] = entry


def touch(cache, url, today: str) -> None:
    """Mark an existing entry as seen today so pruning keeps it."""
    entry = cache.get("entries", {}).get(url)
    if entry:
        entry["seen"] = today


def prune(cache, today: str, max_age_days: int = MAX_AGE_DAYS) -> int:
    """Drop entries not seen within ``max_age_days``. Returns how many removed."""
    try:
        cutoff = (dt.date.fromisoformat(today)
                  - dt.timedelta(days=max_age_days)).isoformat()
    except Exception:
        return 0
    entries = cache.get("entries", {})
    stale = [u for u, e in entries.items() if (e.get("seen") or "") < cutoff]
    for u in stale:
        del entries[u]
    return len(stale)
