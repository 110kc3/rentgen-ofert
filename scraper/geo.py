"""Listing coordinates for the map view (GUGiK UUG geocoder + local cache).

Portals give a locality and sometimes a street — no coordinates. We geocode
the *unique* locality / locality+street strings through the free UUG service
(the same one rcncheck/uldk use), convert EPSG:2180 -> WGS84 in pure Python,
and keep a committed cache (``cache/geo_cache.json``) so CI never re-asks.
Each run does at most ``max_new`` fresh lookups: town names first (one lookup
covers hundreds of listings), then streets by how many listings need them —
so the map is town-accurate immediately and street-accurate over time.

Listings gain ``ll: [lat, lon]`` and ``llp: "s"|"t"`` (street/town precision).
Failed lookups are cached as misses and retried after RETRY_DAYS.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import pathlib
from collections import Counter

from .rcn import _fold
from .uldk import UUG, HEADERS

RETRY_DAYS = 60          # re-ask UUG about a cached miss after this long
DELAY = 0.15             # politeness between UUG calls (seconds)

# ---- EPSG:2180 (PL-1992) -> WGS84 -------------------------------------------
# Transverse Mercator on GRS80: lon0 19°E, k0 0.9993, FE 500 000, FN −5 300 000.
# Standard Snyder inverse series — sub-metre accuracy, no pyproj dependency.
# UUG returns x = easting, y = northing (despite EPSG:2180's official axis
# names) — the same convention uldk.py already passes to GetParcelByXY.

_A = 6378137.0
_F = 1 / 298.257222101
_E2 = _F * (2 - _F)
_EP2 = _E2 / (1 - _E2)
_K0 = 0.9993
_LON0 = math.radians(19.0)
_FE, _FN = 500000.0, -5300000.0
_E1 = (1 - math.sqrt(1 - _E2)) / (1 + math.sqrt(1 - _E2))
_MU_D = _A * (1 - _E2 / 4 - 3 * _E2 ** 2 / 64 - 5 * _E2 ** 3 / 256)


def to_wgs84(x, y):
    """(easting, northing) in EPSG:2180 -> (lat, lon) rounded to ~1 m."""
    mu = (y - _FN) / _K0 / _MU_D
    phi1 = (mu + (3 * _E1 / 2 - 27 * _E1 ** 3 / 32) * math.sin(2 * mu)
            + (21 * _E1 ** 2 / 16 - 55 * _E1 ** 4 / 32) * math.sin(4 * mu)
            + (151 * _E1 ** 3 / 96) * math.sin(6 * mu)
            + (1097 * _E1 ** 4 / 512) * math.sin(8 * mu))
    sin1, cos1, tan1 = math.sin(phi1), math.cos(phi1), math.tan(phi1)
    c1 = _EP2 * cos1 ** 2
    t1 = tan1 ** 2
    n1 = _A / math.sqrt(1 - _E2 * sin1 ** 2)
    r1 = _A * (1 - _E2) / (1 - _E2 * sin1 ** 2) ** 1.5
    d = (x - _FE) / (n1 * _K0)
    lat = phi1 - (n1 * tan1 / r1) * (
        d ** 2 / 2
        - (5 + 3 * t1 + 10 * c1 - 4 * c1 ** 2 - 9 * _EP2) * d ** 4 / 24
        + (61 + 90 * t1 + 298 * c1 + 45 * t1 ** 2 - 252 * _EP2 - 3 * c1 ** 2) * d ** 6 / 720)
    lon = _LON0 + (d - (1 + 2 * t1 + c1) * d ** 3 / 6
                   + (5 - 2 * c1 + 28 * t1 - 3 * c1 ** 2 + 8 * _EP2 + 24 * t1 ** 2) * d ** 5 / 120) / cos1
    return round(math.degrees(lat), 5), round(math.degrees(lon), 5)


# ---- cache -------------------------------------------------------------------

def load(path):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def save(path, cache):
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cache, ensure_ascii=False, separators=(",", ":")),
                 encoding="utf-8")


def _key(locality, street=None):
    k = _fold(locality)
    return f"{k}|{_fold(street)}" if street else k


def _stale(entry, today):
    if entry.get("ll") is not None:
        return False                      # hits never expire
    try:
        age = (dt.date.fromisoformat(today)
               - dt.date.fromisoformat(entry.get("d", "1970-01-01"))).days
    except ValueError:
        return True
    return age >= RETRY_DAYS


def _lookup(session, locality, street, today):
    """One UUG call -> cache entry. Point precision: street when UUG actually
    matched the street, town when it fell back to the city centroid."""
    addr = f"{locality}, {street}" if street else locality
    try:
        r = session.get(UUG, params={"request": "GetAddress", "address": addr},
                        headers=HEADERS, timeout=20)
        r.raise_for_status()
        res = (r.json().get("results") or {}).get("1")
    except Exception:
        return None                       # transient -> don't cache
    if not res:
        return {"ll": None, "d": today}
    lat, lon = to_wgs84(float(res["x"]), float(res["y"]))
    return {"ll": [lat, lon],
            "p": "s" if street and res.get("street") else "t",
            "d": today}


def attach(listings, cache, session, today=None, max_new=500, delay=DELAY,
           log=print):
    """Set ll/llp on listings in place; grow the cache within ``max_new``.

    Returns (new_lookups, located_listings)."""
    import time
    today = today or dt.date.today().isoformat()

    towns = Counter()
    streets = Counter()
    raw = {}                              # key -> (locality, street) for UUG
    for l in listings:
        loc = (l.get("locality") or "").strip()
        if not loc or not _fold(loc):
            continue
        towns[_key(loc)] += 1
        raw.setdefault(_key(loc), (loc, None))
        st = (l.get("street") or "").strip()
        if st and _fold(st):
            k = _key(loc, st)
            streets[k] += 1
            raw.setdefault(k, (loc, st))

    # towns first (max coverage per request), then busiest streets
    wanted = [k for k, _ in towns.most_common()] + [k for k, _ in streets.most_common()]
    new = 0
    for k in wanted:
        if new >= max_new:
            break
        e = cache.get(k)
        if e is not None and not _stale(e, today):
            continue
        entry = _lookup(session, *raw[k], today)
        if entry is None:
            continue
        cache[k] = entry
        new += 1
        time.sleep(delay)

    located = 0
    for l in listings:
        loc = (l.get("locality") or "").strip()
        if not loc:
            continue
        st = (l.get("street") or "").strip()
        hit = None
        if st:
            hit = cache.get(_key(loc, st))
        if not hit or hit.get("ll") is None:
            hit = cache.get(_key(loc))
        if hit and hit.get("ll") is not None:
            l["ll"] = hit["ll"]
            l["llp"] = hit.get("p", "t")
            located += 1
    log(f"  geo: {located}/{len(listings)} listings located "
        f"({new} new UUG lookups, cache {len(cache)})")
    return new, located
