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

The checks run CONCURRENTLY, on a session that does not retry, under a
wall-clock budget. Sequentially and on the shared retry session this phase cost
27-44 minutes of three separate runs for the same 300 questions (runs
31422141701, 31468177600, 31502042693) — its cost is response-time-driven, not
input-driven, because a URL that is really gone answers at once while one that
is live, slow or throttled costs the full timeout and then the retry ladder.
The confirmed-gone counts across those runs (16 / 1 / 0 / 51) track exactly
that split.
"""
from __future__ import annotations

import datetime as dt
import re
import time
from concurrent.futures import ThreadPoolExecutor

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8",
}

GRACE_DAYS = 7          # unseen for this long -> candidate for verification
DEFAULT_MAX_CHECKS = 300
MAX_WORKERS = 8         # as photomatch: the same portals, a tenth of the volume
# A liveness probe that has not answered in this long has told us what it is
# going to tell us. The old 20 s was the shared scraper timeout, appropriate
# for a search page we need the contents of and much too patient for a yes/no.
TIMEOUT = 8
BUDGET_S = 600          # backstop; at 8 workers the phase should be ~5 min

# Portal-specific "this ad is dead" markers on pages that still return 200.
_GONE_MARKERS = re.compile(
    r"og[łl]oszenie\s+(?:jest\s+)?(?:nieaktualne|niedost[ęe]pne|archiwalne|wygas[łl]o|zako[ńn]czone)"
    r"|oferta\s+(?:jest\s+)?(?:nieaktualna|archiwalna|niedost[ęe]pna|zako[ńn]czona)"
    r"|to\s+og[łl]oszenie\s+zosta[łl]o\s+usuni[ęe]te"
    r"|\"availability\"\s*:\s*\"[^\"]*(?:OutOfStock|SoldOut|Discontinued)",
    re.I)

# Redirect landing on a search/index page (portal dumped us off the dead ad).
_INDEX_URL = re.compile(
    r"/(?:oferty|ogloszenia|nieruchomosci|mieszkania|domy|wyniki|d/oferty)/?(?:$|\?)"
    r"|/[a-z-]+\.nieruchomosci-online\.pl/?$")


def last_seen(rec) -> str:
    """Last day the property was seen LIVE. Status-carrying observations (e.g.
    the 'archived' evidence rows observe_archived adds) don't count — otherwise
    an ad archived today would look 'seen today' and the sweep would clear the
    delisted flag that the archive evidence just set."""
    obs = rec.get("observations") or []
    return max((o.get("date") or "" for o in obs if not o.get("status")),
               default=rec.get("first_seen") or "")


def is_gone(url: str, session, timeout: float = TIMEOUT) -> bool | None:
    """True = confirmed gone, False = still live, None = could not tell."""
    try:
        r = session.get(url, headers=HEADERS, timeout=timeout,
                        allow_redirects=True)
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
          log=print, max_workers: int = MAX_WORKERS, budget_s=BUDGET_S,
          probe=is_gone):
    """Mark stale records as delisted (rec['delisted'] = last day it was seen).

    A record seen today (or whose URL is in ``active_urls``) gets any stale
    ``delisted`` flag cleared — the flat came back, that's a relist not a sale.

    ``budget_s`` bounds the wall clock the way the photo phase's does: once
    exceeded the remaining candidates are left unasked (not concluded — they
    keep their place at the front of the oldest-first queue for next run).
    Pass ``session=net.probe_session()``; a retrying session makes each "could
    not tell" cost thirty seconds of nothing.
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
        if urls & active_urls or seen == today:
            if rec.get("delisted"):
                del rec["delisted"]          # resurfaced (visibly live right now)
            continue
        if seen >= cutoff:
            continue                          # too recent to conclude anything
        if rec.get("delisted"):
            continue                          # already concluded
        if rec.get("development"):
            continue    # a vanished developer ad = unit type sold out, not "the flat sold"
        url = next((o.get("url") for o in reversed(rec.get("observations") or [])
                    if o.get("url")), None)
        if url:
            candidates.append((seen, url, rec))

    candidates.sort(key=lambda c: (c[0], c[1]))   # oldest unseen first (never compare the rec dicts)
    todo = candidates[:max_checks]
    deadline = time.monotonic() + budget_s if budget_s else None

    def ask(cand):
        """(answer, was_asked) — the deadline is checked per candidate, so a
        slow start costs the tail of the queue and not the whole run."""
        if deadline is not None and time.monotonic() > deadline:
            return None, False
        return probe(cand[1], session), True

    checked = confirmed = skipped = 0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for (seen, _url, rec), (gone, asked) in zip(todo, ex.map(ask, todo)):
            if not asked:
                skipped += 1
                continue
            checked += 1
            if gone:
                rec["delisted"] = seen
                confirmed += 1
    log(f"  delist sweep: {len(candidates)} stale, {checked} checked, "
        f"{confirmed} confirmed gone"
        + (f"; {skipped} left for next run, sweep budget exhausted"
           if skipped else ""))
    return confirmed
