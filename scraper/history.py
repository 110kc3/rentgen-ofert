"""Persistent property history -> relist detection, price-over-time, lifecycle.

Agents often kill a listing and re-post the same flat under a fresh URL/date to
look "new". They almost always reuse the photos, so we fingerprint each property
by its gallery photo hashes and keep `site/data/history.json` across runs:

    [{ type, area, hashes:[...], first_seen, last_seen,
       observations:[{date, price, url, source, status?}],
       snapshot:{title,image,locality,district,street,rooms,floor,url,source,price},
       photo_urls:[...],          # gallery archive (portal CDN URLs)
       delisted: "YYYY-MM-DD",    # set by delist.sweep when the ad is confirmed gone
       sales:[{date,price,...}]   # set by rcn.match from notarial-deed data
    }]

Each run we match today's properties against that store (same type + ~area +
matching photos; photo-less listings fall back to URL identity so they don't
spawn a fresh record every run). A property whose photos we've seen before
under a *different* URL is flagged as relisted, and its earlier prices are
surfaced. History only grows forward (we can't see listings removed before the
tool first ran) — the RCN sale matcher fills in the deeper past.
"""
from __future__ import annotations

import json
import pathlib
from collections import defaultdict

from .normalize import same_photos

MAX_HASHES = 10       # cap stored gallery hashes per property
MAX_PHOTO_URLS = 8    # cap archived gallery URLs per property
SNAPSHOT_FIELDS = ("title", "image", "locality", "district", "street",
                   "rooms", "floor", "plot_area", "url", "source", "price")


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


def _url_index(records):
    idx = {}
    for r in records:
        for o in r.get("observations") or []:
            u = o.get("url")
            if u:
                idx[u] = r
    return idx


def _update_snapshot(rec, p):
    snap = rec.setdefault("snapshot", {})
    for f in SNAPSHOT_FIELDS:
        v = p.get(f)
        if v not in (None, ""):
            snap[f] = v


def _merge_photo_urls(rec, urls):
    if not urls:
        return
    have = rec.setdefault("photo_urls", [])
    for u in urls:
        if u not in have and len(have) < MAX_PHOTO_URLS:
            have.append(u)


def _observe(rec, p, today, status=None):
    url = p.get("url")
    if not any(o.get("date") == today and o.get("url") == url
               for o in rec["observations"]):
        obs = {"date": today, "price": p.get("price"), "url": url,
               "source": p.get("source")}
        if status:
            obs["status"] = status
        rec["observations"].append(obs)
    rec["last_seen"] = max(rec.get("last_seen") or "", today)


def _match_or_create(records, index, url_idx, p, today):
    hashes = p.get("phashes") or []
    typ, area = p.get("type"), p.get("area")
    # developer ads share marketing photos across many units, so photo identity
    # is meaningless for them — match by URL only
    rec = None if p.get("development") else _find(index, typ, area, hashes)
    if rec is None and p.get("url"):
        cand = url_idx.get(p["url"])
        # URL fallback: only trust it when photos don't contradict it
        if cand is not None and (not hashes or not cand.get("hashes")
                                 or same_photos(hashes, cand["hashes"])):
            rec = cand
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
    if p.get("url"):
        url_idx[p["url"]] = rec
    return rec


def compact(records) -> list:
    """Merge duplicate records that share a listing URL.

    Before the URL-fallback fix, photo-less listings spawned a fresh record on
    every run — same URL, one observation each. Fold each group into the record
    that knows most (has photo hashes, else the oldest), unioning observations.
    """
    by_url = defaultdict(list)
    for r in records:
        for o in r.get("observations") or []:
            if o.get("url"):
                by_url[o["url"]].append(r)

    merged = set()
    for url, group in by_url.items():
        seen_ids = set()
        uniq = []
        for r in group:
            if id(r) not in seen_ids and id(r) not in merged:
                seen_ids.add(id(r))
                uniq.append(r)
        group = uniq
        if len(group) < 2:
            continue
        hashed = [r for r in group if r.get("hashes")]
        if len(hashed) > 1:
            continue                     # photos disagree -> not safe to merge
        keep = hashed[0] if hashed else min(group, key=lambda r: r.get("first_seen") or "9999")
        for r in group:
            if r is keep or id(r) in merged:
                continue
            for o in r.get("observations") or []:
                if not any(x.get("date") == o.get("date") and x.get("url") == o.get("url")
                           for x in keep["observations"]):
                    keep["observations"].append(o)
            for u in r.get("photo_urls") or []:
                if u not in keep.setdefault("photo_urls", []):
                    keep["photo_urls"].append(u)
            snap = keep.setdefault("snapshot", {})
            for k, v in (r.get("snapshot") or {}).items():
                snap.setdefault(k, v)
            keep["first_seen"] = min(keep.get("first_seen") or "9999",
                                     r.get("first_seen") or "9999")
            merged.add(id(r))
        keep["observations"].sort(key=lambda o: o.get("date") or "")
        keep["last_seen"] = max((o.get("date") or "" for o in keep["observations"]),
                                default=keep.get("first_seen") or "")
    return [r for r in records if id(r) not in merged]


def update(properties, records, today: str):
    """Match `properties` to `records`, append today's observations, and enrich
    each property in place with first_seen / relisted / prev_price /
    price_history / timeline / photo_urls / sales."""
    index = defaultdict(list)
    for r in records:
        index[_bucket(r.get("type"), r.get("area"))].append(r)
    url_idx = _url_index(records)

    for p in properties:
        rec = _match_or_create(records, index, url_idx, p, today)
        url = p.get("url")

        if p.get("development"):
            rec["development"] = True

        # the flat is visibly back on the market -> a past "delisted" is stale
        if rec.get("delisted"):
            del rec["delisted"]

        _observe(rec, p, today)
        _update_snapshot(rec, p)
        _merge_photo_urls(rec, p.get("photo_urls"))

        obs = rec["observations"]
        # "na rynku od" = earliest portal publish date we've seen (else first record day)
        pub = sorted((o.get("created") or "")[:10] for o in p.get("offers", []) if o.get("created"))
        p["first_seen"] = min([rec["first_seen"], *pub]) if pub else rec["first_seen"]
        # genuine relist: same property under a DIFFERENT url on an EARLIER day
        # (developments excluded — "the same ad again" is just the developer's
        # rolling marketing, not a flat coming back to the market)
        if rec.get("development"):
            earlier = []
        else:
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
        p["timeline"] = timeline(rec)
        p["photo_urls"] = (rec.get("photo_urls") or [])[:MAX_PHOTO_URLS]
        if rec.get("sales"):
            p["sales"] = rec["sales"]
        p["_rec"] = rec               # transient link for reenrich(); not published
    return records


def reenrich(properties):
    """Refresh timeline/sales on today's listings after a late pass (e.g. RCN
    matching) mutated their history records. Drops the transient _rec link."""
    for p in properties:
        rec = p.pop("_rec", None)
        if rec is None:
            continue
        p["timeline"] = timeline(rec)
        if rec.get("sales"):
            p["sales"] = rec["sales"]


def observe_archived(archived_listings, records, today: str):
    """Feed portal-archived ads (e.g. n-online 'Ogłoszenie archiwalne') into
    history. An archived ad is direct evidence the listing ended — if the
    property isn't live anywhere else, it's marked delisted immediately (no
    grace period, no URL check needed)."""
    index = defaultdict(list)
    for r in records:
        index[_bucket(r.get("type"), r.get("area"))].append(r)
    url_idx = _url_index(records)

    n = 0
    for p in archived_listings:
        # only track archived ads we can identify (by URL we've seen, or photos)
        rec = None
        if p.get("url") and p["url"] in url_idx:
            rec = url_idx[p["url"]]
        elif p.get("phashes"):
            rec = _find(index, p.get("type"), p.get("area"), p["phashes"])
        if rec is None:
            continue
        _observe(rec, p, today, status="archived")
        _update_snapshot(rec, p)
        if not rec.get("delisted"):
            live = [o for o in rec["observations"]
                    if o.get("date") == today and not o.get("status")]
            if not live:
                rec["delisted"] = today
        n += 1
    return n


# ---- timeline (what the dashboard renders) ----------------------------------

def timeline(rec, max_events: int = 24) -> list:
    """Condensed chronological life of a property.

    Event kinds: sale_past (RCN deed before we knew it), listed (first sighting
    on a portal URL), price (price change on the same URL), relist (new URL for
    known photos), archived, delisted, sale (RCN deed after delisting).
    """
    events = []
    for s in rec.get("sales") or []:
        events.append({"date": s["date"],
                       "kind": "sale_past" if s.get("kind") == "past" else "sale",
                       "price": s.get("price"), "market": s.get("market"),
                       "confidence": s.get("confidence"),
                       "addr": s.get("addr"), "dz": s.get("dz")})
    seen_urls = set()
    last_price = {}
    for o in sorted(rec.get("observations") or [], key=lambda o: o.get("date") or ""):
        url, price, date = o.get("url"), o.get("price"), o.get("date")
        if o.get("status") == "archived":
            events.append({"date": date, "kind": "archived", "source": o.get("source"),
                           "url": url})
            continue
        if url not in seen_urls:
            seen_urls.add(url)
            kind = "listed" if len(seen_urls) == 1 else "relist"
            events.append({"date": date, "kind": kind, "price": price,
                           "source": o.get("source"), "url": url})
        elif price is not None and last_price.get(url) is not None \
                and price != last_price.get(url):
            events.append({"date": date, "kind": "price", "price": price,
                           "source": o.get("source"), "url": url})
        if price is not None:
            last_price[url] = price
    if rec.get("delisted"):
        events.append({"date": rec["delisted"], "kind": "delisted"})
    events.sort(key=lambda e: (e.get("date") or "", e.get("kind") != "sale_past"))
    if len(events) > max_events:            # keep first + most recent
        events = events[:2] + events[-(max_events - 2):]
    return events


# ---- archive (delisted properties for the dashboard) ------------------------

def build_archive(records) -> list:
    """Cards for properties that left the market: snapshot + timeline + sales."""
    out = []
    for rec in records:
        if not rec.get("delisted") or rec.get("development"):
            continue
        snap = rec.get("snapshot") or {}
        sales = [s for s in rec.get("sales") or [] if s.get("kind") == "sold"]
        last_obs = max(rec.get("observations") or [{}],
                       key=lambda o: o.get("date") or "")
        out.append({
            "type": rec.get("type"), "area": rec.get("area"),
            "title": snap.get("title"), "image": snap.get("image"),
            "locality": snap.get("locality"), "district": snap.get("district"),
            "rooms": snap.get("rooms"),
            "url": snap.get("url") or last_obs.get("url"),
            "source": snap.get("source") or last_obs.get("source"),
            "price": last_obs.get("price") or snap.get("price"),
            "first_seen": rec.get("first_seen"),
            "delisted": rec.get("delisted"),
            "sold": sales[-1] if sales else None,
            "timeline": timeline(rec),
            "photo_urls": (rec.get("photo_urls") or [])[:MAX_PHOTO_URLS],
        })
    out.sort(key=lambda a: a.get("delisted") or "", reverse=True)
    return out
