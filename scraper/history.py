"""Persistent property history -> relist detection and price-over-time.

Agents often kill a listing and re-post the same flat under a fresh URL/date to
look "new". They almost always reuse the photos, so we fingerprint each property
by its gallery photo hashes and keep `site/data/history.json` across runs:

    [{ type, area, hashes:[...], first_seen, observations:[{date,price,url,source}] }]

Each run we match today's properties against that store (same type + ~area +
matching photos). A property whose photos we've seen before under a *different*
URL is flagged as relisted, and its earlier prices are surfaced. History only
grows forward (we can't see listings removed before the tool first ran).
"""
from __future__ import annotations

import json
import pathlib
from collections import defaultdict

from .normalize import same_photos

MAX_HASHES = 10  # cap stored gallery hashes per property


def _bucket(typ, area):
    return (typ, int(round(area))) if area is not None else (typ, None)


def load(path) -> list:
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except Exception:
        return []


def save(path, records):
    pathlib.Path(path).write_text(
        json.dumps(records, ensure_ascii=False, indent=0), encoding="utf-8")


def _find(rec_index, typ, area, hashes):
    if not hashes:
        return None
    buckets = [(typ, b) for b in (
        (int(round(area)) - 1, int(round(area)), int(round(area)) + 1) if area is not None else (None,))]
    for b in buckets:
        for r in rec_index.get(b, []):
            if same_photos(hashes, r.get("hashes", [])):
                return r
    return None


def update(properties, records, today: str):
    """Match `properties` to `records`, append today's observations, and enrich
    each property in place with first_seen / relisted / prev_price / price_history."""
    index = defaultdict(list)
    for r in records:
        index[_bucket(r.get("type"), r.get("area"))].append(r)

    for p in properties:
        hashes = p.get("phashes") or []
        typ, area, url, price = p.get("type"), p.get("area"), p.get("url"), p.get("price")
        rec = _find(index, typ, area, hashes)
        if rec is None:
            rec = {"type": typ, "area": area, "hashes": list(hashes[:MAX_HASHES]),
                   "first_seen": today, "observations": []}
            records.append(rec)
            index[_bucket(typ, area)].append(rec)
        else:
            for h in hashes:
                if h not in rec["hashes"]:
                    rec["hashes"].append(h)
            rec["hashes"] = rec["hashes"][:MAX_HASHES]

        if not any(o.get("date") == today and o.get("url") == url for o in rec["observations"]):
            rec["observations"].append(
                {"date": today, "price": price, "url": url, "source": p.get("source")})

        obs = rec["observations"]
        # "na rynku od" = earliest portal publish date we've seen (else first record day)
        pub = sorted((o.get("created") or "")[:10] for o in p.get("offers", []) if o.get("created"))
        p["first_seen"] = min([rec["first_seen"], *pub]) if pub else rec["first_seen"]
        # genuine relist: same property under a DIFFERENT url on an EARLIER day
        earlier = [o for o in obs if o.get("url") != url and (o.get("date") or "") < today]
        p["relisted"] = bool(earlier)
        p["prev_price"] = next((o["price"] for o in reversed(earlier) if o.get("price")), None)
        # price trail: points where the price changed over time
        trail, last = [], object()
        for o in obs:
            if o.get("price") != last:
                trail.append({"date": o["date"], "price": o.get("price")})
                last = o.get("price")
        p["price_history"] = trail
    return records
