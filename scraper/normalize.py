"""Shared schema, value helpers and cross-portal de-duplication.

Each scraper yields a raw listing dict:

    source source_id url title type price area price_per_m2 rooms
    plot_area floor district street is_private agency image created

`dedupe()` groups listings that look like the same property into one record:

    offers     [{source, url, price, price_per_m2, created, is_private, agency}]
    sources    sorted distinct portal names
    price      lowest offer price        price_max  highest offer price
    cheapest   the single lowest-priced offer (for highlighting)
    created    most recent date across offers

Merge rule (fast "by size", as chosen): listings merge when they share
    flats:  type + exact area (m2) + room count
    houses: type + exact area (m2)                   (OLX omits house rooms)
Price is intentionally allowed to differ - the same flat is often re-posted at
different prices - EXCEPT a merged group may span at most +15% in price
(SPREAD_CAP), so a 0.8M and a 1.8M "220 m2" house are not lumped together. This is
deliberately loose and can merge distinct same-size properties (e.g. identical
new-build units); the trade-off was chosen for coverage over precision.
"""
from __future__ import annotations

from collections import defaultdict

CITY = "Gliwice"

OTODOM_ROOMS = {
    "ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5,
    "SIX": 6, "SEVEN": 7, "EIGHT": 8, "NINE": 9, "TEN": 10,
}
OLX_ROOMS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}
SOURCE_RANK = {"otodom": 0, "nieruchomosci-online": 1, "gratka": 2, "olx": 3}

DISPLAY_FIELDS = ("title", "type", "area", "rooms", "plot_area", "floor",
                  "locality", "district", "street", "image", "is_private", "agency",
                  "market")
OFFER_FIELDS = ("source", "url", "price", "price_per_m2", "created",
                "is_private", "agency")

SPREAD_CAP = 1.15  # a merged size-group may span at most +15% in price (fallback)
PHOTO_THRESHOLD = 40  # max dHash hamming to treat two galleries as the same property

# --- developer new-builds ----------------------------------------------------
# Developers post many units with the same marketing photos, which the
# "same size + same gallery" rule would wrongly collapse into one property
# (and pollute relist/sold history). Detect them and treat them separately.
import re as _re

_DEV_RE = _re.compile(
    r"deweloper|inwestycj|rynek\s+pierwotn|nowe\s+osiedle|stan\s+deweloperski"
    r"|etap\s+[ivx0-9]", _re.I)


def is_development(l) -> bool:
    """Portal says rynek pierwotny, or the title reads like a developer ad."""
    if (l.get("market") or "").startswith(("primary", "pierwotn")):
        return True
    return bool(_DEV_RE.search(l.get("title") or ""))


def _cluster_is_development(members) -> bool:
    """A photo-cluster is a development when any ad self-identifies as one, or
    one portal contributed >=3 distinct ads with the same gallery (an owner or
    agency duplicates 1-2x; a developer posts a whole staircase)."""
    if any(is_development(m) for m in members):
        return True
    per_source = {}
    for m in members:
        key = (m.get("source"), m.get("source_id"))
        per_source.setdefault(m.get("source"), set()).add(key)
    return any(len(ids) >= 3 for ids in per_source.values())


def otodom_rooms(value):
    if value is None:
        return None
    return OTODOM_ROOMS.get(str(value).strip().upper())


def olx_rooms(value):
    if value is None:
        return None
    v = str(value).strip().lower()
    return int(v) if v.isdigit() else OLX_ROOMS.get(v)


def to_float(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = "".join(ch for ch in str(value).replace("\xa0", "").replace(" ", "").replace(",", ".")
                if ch.isdigit() or ch in ".-")
    try:
        return float(s)
    except ValueError:
        return None


def to_int(value):
    f = to_float(value)
    return int(round(f)) if f is not None else None


def size_key(l):
    """Group key by size. Area must match EXACTLY (to 0.01 m2) - no rounding, so
    a 49.6 and a 50.4 m2 flat are never merged. Houses ignore rooms (OLX omits
    them); flats also key on room count."""
    area = l.get("area")
    if area is None:
        return None
    typ, area_m = l.get("type"), round(area, 2)
    return (typ, area_m) if typ == "house" else (typ, area_m, l.get("rooms"))


def _split_by_price(members):
    """Split a size-group so each cluster spans at most SPREAD_CAP (cheapest x1.15).

    Listings are sorted by price; a new cluster starts whenever a price exceeds
    the current cluster's cheapest by more than SPREAD_CAP. This bounds how far
    apart prices in one merged card can be, so clearly-different same-size flats
    (or a 0.8M vs 1.8M house) are not lumped together.
    """
    priced = sorted((m for m in members if m.get("price") is not None),
                    key=lambda m: m["price"])
    unpriced = [m for m in members if m.get("price") is None]
    clusters, cur, cur_min = [], [], None
    for m in priced:
        if cur and m["price"] > cur_min * SPREAD_CAP:
            clusters.append(cur)
            cur, cur_min = [], None
        if not cur:
            cur_min = m["price"]
        cur.append(m)
    if cur:
        clusters.append(cur)
    if not clusters:
        return [unpriced] if unpriced else []
    clusters[0] = unpriced + clusters[0]
    return clusters


def _rank(l):
    return (0 if l.get("image") else 1,
            SOURCE_RANK.get(l.get("source"), 9),
            l.get("price") if l.get("price") is not None else float("inf"))


def _build(members):
    members = sorted(members, key=_rank)
    prop = {}
    for f in DISPLAY_FIELDS:
        prop[f] = next((m.get(f) for m in members if m.get(f) not in (None, "")), None)
    offers, seen = [], set()
    for m in members:
        if m.get("url") in seen:
            continue
        seen.add(m.get("url"))
        offers.append({k: m.get(k) for k in OFFER_FIELDS})
    offers.sort(key=lambda o: (o["price"] is None, o["price"] or 0))
    prices = [o["price"] for o in offers if o["price"] is not None]
    dates = [o["created"] for o in offers if o["created"]]
    primary = members[0]
    phashes, photo_urls = [], []
    for m in members:
        for h in (m.get("phashes") or []):
            if h not in phashes:
                phashes.append(h)
        for u in (m.get("photo_urls") or []):
            if u not in photo_urls:
                photo_urls.append(u)
    prop["phashes"] = phashes
    prop["photo_urls"] = photo_urls
    prop.update({
        "source": primary.get("source"),
        "url": primary.get("url"),
        "price": min(prices) if prices else None,
        "price_max": max(prices) if prices else None,
        "price_per_m2": primary.get("price_per_m2"),
        "cheapest": offers[0] if offers and offers[0]["price"] is not None else None,
        "created": max(dates) if dates else None,
        "sources": sorted({o["source"] for o in offers}, key=lambda s: SOURCE_RANK.get(s, 9)),
        "offers": offers,
    })
    return prop


def _hamming(a, b):
    return bin(a ^ b).count("1")


def same_photos(a_hashes, b_hashes):
    """True if the closest pair of gallery hashes is within PHOTO_THRESHOLD."""
    if not a_hashes or not b_hashes:
        return False
    return min(_hamming(a, b) for a in a_hashes for b in b_hashes) <= PHOTO_THRESHOLD


def _photo_clusters(members):
    """Cluster a size-group by matching photos; un-photographed ads stay alone."""
    n = len(members)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(n):
        for j in range(i + 1, n):
            if same_photos(members[i].get("phashes") or [], members[j].get("phashes") or []):
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[ri] = rj

    clusters = {}
    for i in range(n):
        clusters.setdefault(find(i), []).append(members[i])
    return list(clusters.values())


def dedupe(listings):
    groups = defaultdict(list)
    loners = []
    for l in listings:
        k = size_key(l)
        (loners if k is None else groups[k]).append(l)

    def _build_dev(cluster):
        """One card per distinct asking price (~unit type) inside a development
        cluster; identical units listed on several portals still merge."""
        by_price = defaultdict(list)
        for m in cluster:
            by_price[m.get("price")].append(m)
        out = []
        for price_members in by_price.values():
            prop = _build(price_members)
            prop["development"] = True
            out.append(prop)
        return out

    properties = []
    for l in loners:
        prop = _build([l])
        if is_development(l):
            prop["development"] = True
        properties.append(prop)
    for members in groups.values():
        if len(members) == 1:
            prop = _build(members)
            if is_development(members[0]):
                prop["development"] = True
            properties.append(prop)
        elif any(m.get("phashes") for m in members):
            # photos available -> merge only ads whose galleries match
            for cluster in _photo_clusters(members):
                if _cluster_is_development(cluster):
                    properties.extend(_build_dev(cluster))
                else:
                    properties.append(_build(cluster))
        else:
            # no photo data -> fall back to the size + price-spread heuristic
            dev = _cluster_is_development(members)
            for cluster in _split_by_price(members):
                if dev:
                    properties.extend(_build_dev(cluster))
                else:
                    properties.append(_build(cluster))
    return properties


def link_same_size(properties):
    """Flag the same flat listed more than once via the one thing that can't
    change on a re-post: floor area. Properties sharing exact area + rooms +
    locality that photo-dedup kept apart are very likely the same flat re-listed
    (photos swapped). Sets `relisted`, `prev_price`, `also_listed`. Big clusters
    (developments of identical units) are skipped to avoid false positives."""
    groups = defaultdict(list)
    for p in properties:
        if p.get("development"):
            continue
        area = p.get("area")
        loc = (p.get("street") or p.get("locality") or "").strip().lower()
        if area is None or not loc:
            continue
        groups[(p.get("type"), round(area, 2), p.get("rooms"), loc)].append(p)

    for members in groups.values():
        urls = {m.get("url") for m in members}
        if not (2 <= len(urls) <= 3):          # 2-3 = likely relist; more = a development
            continue
        for p in members:
            others = [m for m in members if m.get("url") != p.get("url")]
            if not others:
                continue
            p["relisted"] = True
            p["also_listed"] = [{"price": o.get("price"), "url": o.get("url"),
                                 "source": o.get("source"), "first_seen": o.get("first_seen")}
                                for o in others]
            cheaper = [o.get("price") for o in others if o.get("price") is not None]
            if cheaper:
                p["prev_price"] = min(cheaper)
    return properties
