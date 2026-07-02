"""Verify that a listing is really gone before declaring it delisted.

Region searches are pagination-capped (newest N pages), so an old listing can
drop out of a scrape while still being live — absence alone is weak evidence.
For history records that haven't been seen for GRACE_DAYS we fetch the last
known URL directly:

  * HTTP 404 / 410 / redirect to a listing-index page  -> gone
  * page body carries the portal's "expired/archived" marker -> gone
  * anything else (200 with a live ad, network error)  -> keep waiting

At most ``max_checks`` URLs are verified per run (oldest first), so a run's
extra traffic stays bounded; the rest are retried on later runs.
"""
from __future__ import annotations

import datetime as dt
import re

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8",
}

GRACE_DAYS = 7          # unseen for this long -> candidate for verification
DEFAULT_MAX_CHECKS = 300

# Portal-specific "this ad is dead" markers on pages that still return 200.
_GONE_MARKERS = re.compile(
    r"og[łl]oszenie\s+(?:jest\s+)?(?:nieaktualne|niedost[ęe]pne|archiwalne|wygas[łl]o)"
    r"|oferta\s+(?:jest\s+)?(?:nieaktualna|archiwalna|niedost[ęe]pna)"
    r"|to\s+og[łl]oszenie\s+zosta[łl]o\s+usuni[ęe]te"
    r"|zako[ńn]czone|\"availability\"\s*:\s*\"[^\"]*(?:OutOfStock|SoldOut|Discontinued)",
    re.I)

# Redirect landing on a search/index page (portal dumped us off the dead ad).
_INDEX_URL = re.compile(
    r"/(?:oferty|ogloszenia|nieruchomosci|mieszkania|domy|wyniki|d/oferty)/?(?:$|\?)"
    r"|/[a-z-]+\.nieruchomosci-online\.pl/?$")


def last_seen(rec) -> str:
    obs = rec.get("observations") or []
    return max((o.get("date") or "" for o in obs), default=rec.get("first_seen") or "")


def is_gone(url: str, session) -> bool | None:
    """True = confirmed gone, False = still live, None = could not tell."""
    try:
        r = session.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
    except Exception:
        return None
    if r.status_code in (404, 410):
        return True
    if r.history and _INDEX_URL.search(r.url or ""):
        return True          # redirected off the ad onto an index page
    if r.status_code != 200:
        return None
    if _GONE_MARKERS.search(r.text or ""):
        return True
    return False


def sweep(records, today: str, session, active_urls=None,
          max_checks: int = DEFAULT_MAX_CHECKS, grace_days: int = GRACE_DAYS,
          log=print):
    """Mark stale records as delisted (rec['delisted'] = last day it was seen).

    A record seen today (or whose URL is in ``active_urls``) gets any stale
    ``delisted`` flag cleared — the flat came back, that's a relist not a sale.
    """
    active_urls = active_urls or set()
    try:
        cutoff = (dt.date.fromisoformat(today)
                  - dt.timedelta(days=grace_days)).isoformat()
    except ValueError:
        return 0

    candidates = []
    for rec in records:
        seen = last_seen(rec)
        urls = {o.get("url") for o in rec.get("observations") or []}
        if urls & active_urls or seen >= cutoff:
            if rec.get("delisted"):
                del rec["delisted"]          # resurfaced
            continue
        if rec.get("delisted"):
            continue                          # already concluded
        if rec.get("development"):
            continue    # a vanished developer ad = unit type sold out, not "the flat sold"
        url = next((o.get("url") for o in reversed(rec.get("observations") or [])
                    if o.get("url")), None)
        if url:
            candidates.append((seen, url, rec))

    candidates.sort()                         # oldest unseen first
    checked = confirmed = 0
    for seen, url, rec in candidates:
        if checked >= max_checks:
            break
        checked += 1
        gone = is_gone(url, session)
        if gone:
            rec["delisted"] = seen
            confirmed += 1
    log(f"  delist sweep: {len(candidates)} stale, {checked} checked, "
        f"{confirmed} confirmed gone")
    return confirmed
