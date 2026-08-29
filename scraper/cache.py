"""Persistent photo-hash cache: skip re-fetching photos we've already hashed.

`photomatch` hashes a search-card cover for cold correctness work or fetches an
ambiguous listing's detail page plus a few gallery images for history. The
result is keyed by listing URL and reused on later runs.

The cache lives in ``cache/phash_<region>.json.gz`` (committed, so the GitHub
Actions job reuses it run-to-run) and self-prunes URLs not seen for
``MAX_AGE_DAYS`` so it can't grow without bound:

    {"version": 2, "entries": {url: {"h": ["<base64>", ...], "seen": "YYYY-MM-DD",
                                     "urls": ["https://...", ...],
                                     "scope": "cover"}},
     "backlog": {url: "YYYY-MM-DD"}}

**Why gzip + base64.** The v1 file wrote each 256-bit dHash as a ~78-character
decimal string in plain JSON. At 34 137 listings that reached 62.86 MB, past
GitHub's 50 MB warning and on course for the 100 MB hard limit that would make
the run's push simply fail — a ceiling a second region would hit immediately.
Base64 of the 32 raw bytes is 44 chars, and the file is gzipped like the history
and RCN snapshots already are.

v1 files are read transparently (decimal strings still parse) and rewritten in
v2 on the next save, so the migration needs no separate step.

"urls" (the image URLs the hashes came from) is optional — old entries lack it.
"scope" is present for the cheaper search-card path; absent means the normal
detail-page gallery. It applies to positive hashes *and* empty attempts. That
last part is correctness-critical during migration: a legacy "gallery blocked"
verdict must not suppress an accessible card cover, while a repeatedly failed
cover should still get the normal one-week negative-cache rest.

**Negative entries.** A listing whose gallery yields nothing is recorded as a
miss rather than skipped, because "no photos" was previously never cached at
all: morizon served its galleries from a host `photomatch` didn't match, so all
9 505 morizon detail pages were re-fetched every single run, always returned
nothing, and competed for the same photo budget that was starving 15 350 other
listings. A miss is retried ``MISS_RETRIES`` times (a fetch can fail
transiently) and then believed for ``MISS_RECHECK_DAYS``, so a portal that
genuinely has no photos for us costs one probe a week instead of one a run,
and a portal that starts serving them again is picked back up.

**Budget backlog.** A cold region can contain more uncached listings than the
photo budget can inspect in one run. Deferred URLs live in the top-level
``backlog`` map with the date they first waited. This is deliberately separate
from a negative cache entry: "not attempted" must never become "no photos".
The next run can therefore put older deferred work ahead of fresh ads and
report backlog age/count instead of emitting one ephemeral log line.
"""
from __future__ import annotations

import base64
import datetime as dt
import gzip
import json
import os
import pathlib

VERSION = 2
MAX_AGE_DAYS = 21     # drop a URL we haven't seen in this many days
MISS_RETRIES = 3      # empty results tolerated before "this ad has no photos"
MISS_RECHECK_DAYS = 7 # ... and how long that verdict stands before re-probing

HASH_BYTES = 32       # dHash is 256-bit (photomatch.dhash at size=16)


def pack(h: int) -> str:
    """256-bit hash -> 44-char base64 (vs ~78 chars as a decimal string)."""
    return base64.b64encode(int(h).to_bytes(HASH_BYTES, "big")).decode("ascii")


def unpack(s) -> int:
    """Read a hash in either encoding: v2 base64, or a v1 decimal string."""
    if isinstance(s, int):
        return s
    text = str(s)
    if text.lstrip("-").isdigit():        # v1
        return int(text)
    return int.from_bytes(base64.b64decode(text), "big")


def _paths(path):
    """(gzipped path, legacy plain-json path) for a configured cache path."""
    p = pathlib.Path(path)
    if p.suffix == ".gz":
        return p, p.with_suffix("")       # …json.gz -> …json
    return p.with_name(p.name + ".gz"), p


def _to_v2(data: dict) -> dict:
    """Re-encode v1 decimal-string hashes in place. One pass, then never again."""
    if data.get("version") == VERSION:
        return data
    for entry in data.get("entries", {}).values():
        old = entry.pop("hashes", None)
        if old is None:
            continue
        try:
            entry["h"] = [pack(unpack(h)) for h in old]
        except (TypeError, ValueError):
            entry["h"] = []
    data["version"] = VERSION
    return data


def load(path) -> dict:
    gz, plain = _paths(path)
    for p, opener in ((gz, gzip.open), (plain, open)):
        try:
            with opener(p, "rt", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict) and isinstance(data.get("entries"), dict):
                return _to_v2(data)
        except Exception:
            continue
    return {"version": VERSION, "entries": {}}


def save(path, cache) -> None:
    gz, plain = _paths(path)
    cache["version"] = VERSION
    gz.parent.mkdir(parents=True, exist_ok=True)
    tmp = gz.with_name(gz.name + ".tmp")   # atomic: never leave a truncated cache
    with gzip.open(tmp, "wt", encoding="utf-8") as fh:
        json.dump(cache, fh, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, gz)
    # a v1 file left behind would be stale AND huge — the whole point is to stop
    # pushing it
    if plain != gz and plain.exists():
        plain.unlink()


def _hashes(entry):
    return entry.get("h", entry.get("hashes")) or []


def get(cache, url, today: str = None):
    """Cached photo hashes for ``url``.

    Returns a list of ints on a hit, ``[]`` for "we know this ad has no photos
    for us", and None when it should be fetched. Callers must distinguish []
    from None — an empty list is a cache HIT (see the module docstring).
    """
    entry = cache.get("entries", {}).get(url)
    if not entry:
        return None
    raw = _hashes(entry)
    if raw:
        try:
            return [unpack(h) for h in raw]
        except (TypeError, ValueError):
            return None
    if entry.get("miss", 0) < MISS_RETRIES:
        return None                        # still inside the retry allowance
    tried = entry.get("tried") or entry.get("seen")
    if today and tried and _days_between(tried, today) >= MISS_RECHECK_DAYS:
        return None                        # verdict has aged out — probe again
    return []


def _days_between(a: str, b: str) -> int:
    try:
        return (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days
    except Exception:
        return 0


def get_urls(cache, url):
    """Cached source image URLs for ``url`` (may be [] for old entries)."""
    entry = cache.get("entries", {}).get(url)
    return list(entry.get("urls") or []) if entry else []


def get_scope(cache, url) -> str:
    """``cover`` for a search-card hash, otherwise ``gallery``.

    Gallery is the backward-compatible default: every cache entry written
    before the scope field existed came from the detail-page gallery path.
    """
    entry = cache.get("entries", {}).get(url) or {}
    return "cover" if entry.get("scope") == "cover" else "gallery"


def put(cache, url, hashes, today: str, image_urls=None, scope=None) -> None:
    """Store a photo result for ``url``, stamped as seen ``today``.

    An empty result is recorded as a miss (see the module docstring) rather
    than dropped, so a permanently photo-less ad stops being re-fetched every
    run. Its retry counter keeps climbing until MISS_RETRIES, at which point
    ``get`` starts answering [] instead of None.
    """
    if not url:
        return
    entries = cache.setdefault("entries", {})
    if not hashes:
        prev = entries.get(url) or {}
        if _hashes(prev):
            return          # had photos before; a blank read now is a blip
        next_scope = "cover" if scope == "cover" else "gallery"
        # Gallery and cover are independent ways to obtain evidence. Three old
        # detail-page failures say nothing about the newly available card CDN;
        # reset the allowance when changing path instead of immediately
        # believing the first cover failure.
        previous_misses = (prev.get("miss") or 0) if (
            prev and get_scope(cache, url) == next_scope
        ) else 0
        entry = {"h": [], "seen": today, "tried": today,
                 "miss": previous_misses + 1}
        if next_scope == "cover":
            entry["scope"] = "cover"
        entries[url] = entry
        return
    entry = {"h": [pack(h) for h in hashes], "seen": today}
    if image_urls:
        entry["urls"] = list(image_urls)
    if scope == "cover":
        entry["scope"] = "cover"
    entries[url] = entry


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


def backlog(cache) -> dict:
    """Return the persisted ``url -> first deferred date`` map.

    Be conservative when reading an older or hand-edited cache: malformed
    backlog values are ignored rather than making photo hashing fail before it
    starts. Cache entries themselves remain subject to the stricter loader
    checks above because corrupt hashes affect identity.
    """
    raw = cache.get("backlog") or {}
    if not isinstance(raw, dict):
        return {}
    clean = {}
    for url, date in raw.items():
        if not url or not isinstance(date, str) or not date:
            continue
        try:
            dt.date.fromisoformat(date)
        except ValueError:
            continue
        clean[str(url)] = date
    return clean


def update_backlog(cache, deferred_urls, today: str) -> dict:
    """Replace the budget backlog and return its compact persisted summary.

    URLs that are still deferred retain their original date; attempted,
    cached, twinned, and vanished URLs drop out. Replacing the map rather than
    appending to it keeps a regional cache from retaining dead work forever.
    """
    previous = backlog(cache)
    urls = sorted({str(url) for url in deferred_urls if url})
    current = {url: previous.get(url, today) for url in urls}
    cache["backlog"] = current
    oldest = min(current.values(), default=None)
    return {
        "count": len(current),
        "oldest": oldest,
        "age_days": _days_between(oldest, today) if oldest else 0,
    }
