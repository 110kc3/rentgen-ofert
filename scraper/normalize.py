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
different prices. When photo matching is explicitly disabled, a merged group
may span at most +15% in price (SPREAD_CAP), so a 0.8M and a 1.8M "220 m2" house
are not lumped together. With photo matching enabled, callers disable that
heuristic: an all-unresolved size group stays as separate ads, while exact
portal-ID twins still merge. Under-deduplication is safer than inventing one
property from several same-size listings.
"""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict

from .regions import catalog
from .identity import compatible

OTODOM_ROOMS = {
    "ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5,
    "SIX": 6, "SEVEN": 7, "EIGHT": 8, "NINE": 9, "TEN": 10,
}
OLX_ROOMS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}
SOURCE_RANK = {"otodom": 0, "nieruchomosci-online": 1, "gratka": 2, "olx": 3,
               "morizon": 4}

# Gratka/Morizon breadcrumbs end with the voivodeship. Derive every accepted
# spelling from the canonical catalog so adding or correcting a Polish label
# cannot leave parsing with a second handwritten 16-region list.
VOIVODESHIPS = frozenset(
    value.lower()
    for entry in catalog()["regions"]
    for value in (entry["adjective"], entry["label"])
)


def region_slug(value):
    """Normalize a Polish voivodeship label to the repository's URL slug.

    Portal result pages can carry promoted cards from outside the requested
    region. Their address metadata uses labels such as ``"śląskie"`` while
    ``RENTGEN_REGION`` uses ``"slaskie"``; comparing this normalized form lets
    scrapers reject those cards before one leaked locality expands another
    portal's town crawl.
    """
    # Unicode does not decompose Polish ł/Ł under NFKD.
    folded = unicodedata.normalize(
        "NFKD", str(value or "").translate(str.maketrans({"ł": "l", "Ł": "L"})))
    ascii_value = "".join(c for c in folded if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")


def location_parts(location):
    """'Żerniki, Gliwice, śląskie' -> ['Żerniki', 'Gliwice'] (voivodeship dropped)."""
    parts = [p.strip() for p in (location or "").split(",") if p.strip()]
    if parts and parts[-1].lower() in VOIVODESHIPS:
        parts = parts[:-1]
    return parts


# gratka and morizon (same media group, same frontend) put the search's total
# in the meta description: "Mieszkania na sprzedaż śląskie. 9856 ogłoszeń." on
# gratka, "Mieszkania na sprzedaż - ponad 9000 ogłoszeń" on morizon. That total
# is the only thing that distinguishes "the results ran out" from "the portal
# 404s past page 200" — both of which the page loop sees as a 404.
# `\s` covers the non-breaking and narrow spaces the portals group digits with
_STATED_TOTAL = re.compile(r"(ponad\s+)?(\d[\d\s.]*)\s*ogłosze", re.I)


def stated_total(html):
    """(total, is_min) from a gratka/morizon results page, or (None, False).

    morizon says "ponad 9000" and rounds to whole thousands, so its number is a
    LOWER bound: below it proves truncation, above it proves nothing.
    """
    m = _STATED_TOTAL.search(html or "")
    if not m:
        return None, False
    digits = re.sub(r"[^\d]", "", m.group(2))
    if not digits:
        return None, False
    return int(digits), bool(m.group(1))

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
    # keep price and zł/m² consistent: both from the CHEAPEST offer's listing
    # (card price is the min across portals; primary's ppm may belong to a
    # pricier offer of the same flat)
    cheapest = offers[0] if offers and offers[0]["price"] is not None else None
    ppm = primary.get("price_per_m2")
    if cheapest:
        cheap_member = next((m for m in members if m.get("url") == cheapest["url"]), None)
        if cheap_member and cheap_member.get("price_per_m2") is not None:
            ppm = cheap_member["price_per_m2"]
        elif prop.get("area"):
            ppm = round(cheapest["price"] / prop["area"])
    prop.update({
        "source": primary.get("source"),
        "url": primary.get("url"),
        "price": min(prices) if prices else None,
        "price_max": max(prices) if prices else None,
        "price_per_m2": ppm,
        "cheapest": cheapest,
        "created": max(dates) if dates else None,
        "sources": sorted({o["source"] for o in offers}, key=lambda s: SOURCE_RANK.get(s, 9)),
        "offers": offers,
    })
    return prop


def require_unique_urls(listings, stage="listings"):
    """Fail with useful provenance when one URL represents multiple records.

    A portal URL identifies one advertisement independently of type, area or
    price. Letting it enter two normalization groups creates duplicate index
    cards and silently overwrites one detail-shard entry. Keep this invariant
    close to normalization as well as in the final generated-data validator so
    a bad scrape fails before photo/history/RCN work.
    """
    by_url = defaultdict(list)
    for listing in listings:
        url = listing.get("url")
        if url:
            by_url[url].append(listing)
    duplicates = {url: rows for url, rows in by_url.items() if len(rows) > 1}
    if not duplicates:
        return listings

    lines = [f"{stage} contains {len(duplicates)} duplicate URL(s)"]
    for url, rows in sorted(duplicates.items()):
        details = ", ".join(
            f"source={row.get('source') or '?'} "
            f"source_id={row.get('source_id') or '?'} "
            f"type={row.get('type') or '?'} "
            f"area={row.get('area')!r} price={row.get('price')!r}"
            for row in rows
        )
        lines.append(f"{url}: {details}")
    raise ValueError("\n".join(lines))


def take_unseen(items, seen, key="url"):
    """Return records whose identity is new, including within this batch.

    A list comprehension followed by ``seen.update`` only removes records seen
    on earlier pages; two clones on the same page both pass before ``seen`` is
    updated. Portal result pages do contain such clones, so mutate ``seen`` as
    each item is accepted.
    """
    fresh = []
    for item in items:
        identity = item.get(key)
        if not identity or identity in seen:
            continue
        seen.add(identity)
        fresh.append(item)
    return fresh


def _hamming(a, b):
    return bin(a ^ b).count("1")


def same_photos(a_hashes, b_hashes):
    """True if any pair of gallery hashes is within PHOTO_THRESHOLD.

    any() short-circuits on the first hit — this runs O(properties x bucket)
    times in history matching, so not evaluating the full cross product matters."""
    if not a_hashes or not b_hashes:
        return False
    return any(_hamming(a, b) <= PHOTO_THRESHOLD for a in a_hashes for b in b_hashes)


def _photo_clusters(members):
    """Photo clusters cannot contain contradictory known property attributes.

    Seed exact portal-ID twins first. Check every member before union so an
    unknown-location bridge cannot join two known, different towns transitively.
    """
    groups = _union_twins([[member] for member in members])
    n = len(groups)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(n):
        for j in range(i + 1, n):
            ri, rj = find(i), find(j)
            if ri == rj:
                continue
            left, right = groups[ri], groups[rj]
            if (any(same_photos(a.get("phashes") or [], b.get("phashes") or [])
                    for a in left for b in right)
                    and all(compatible(a, b) for a in left for b in right)):
                parent[ri] = rj
                groups[rj].extend(left)

    return [group for i, group in enumerate(groups) if find(i) == i]


def link_twins(listings):
    """Pair morizon ads with the gratka ad they ARE, by portal id.

    gratka and morizon are one database behind two frontends, and a morizon
    card's thumbnail is a base64-wrapped origin on gratka's own CDN carrying
    gratka's ad id (see ``photomatch.gratka_ad_id``). That id is identity, not
    resemblance, so this needs no photos, no threshold and no extra request —
    which matters because these two portals contribute equal, fully overlapping
    piles: 9 505 listings each in the 2026-08-08 run, of which morizon merged
    with *nothing* and shipped ~7 000 duplicate cards.

    Paired listings inherit gratka's size so they land in the same size group
    (the areas disagree often enough to matter), and carry a shared ``_twin``
    that ``dedupe`` unions on regardless of what the photos say.

    The morizon half also gets ``_identified_by``, naming the gratka ad that
    settles its identity. Nothing needs its photos after that — the pair merges
    on the id, and `_build` unions the gratka half's hashes onto the property —
    so `photomatch.attach_hashes` skips it and spends the fetch on a listing
    that is still ambiguous. That is ~8 700 detail fetches a run (measured on
    the published 2026-08-11 data), against a photo phase that was starving
    9 177-18 296 listings of a budget it could not stretch. Run this BEFORE
    hashing for that to pay; `dedupe` calls it again, idempotently, because the
    linking must also hold when hashing is off entirely.
    """
    by_ad = {}
    for l in listings:
        if l.get("source") == "gratka" and l.get("source_id"):
            by_ad[str(l["source_id"])] = l
    linked = 0
    for l in listings:
        if l.get("source") != "morizon" or not l.get("gratka_id"):
            continue
        twin = by_ad.get(str(l["gratka_id"]))
        if twin is None or twin.get("type") != l.get("type"):
            continue
        key = f"gratka:{l['gratka_id']}"
        l["_twin"] = twin["_twin"] = key
        l["_identified_by"] = twin.get("url")
        # One of them donates the size to the other, so the pair shares a
        # size_key — otherwise a disagreement over usable-vs-total m2 puts them
        # in different groups. gratka is the origin portal so it goes first, but
        # either will do; what matters is that they agree.
        donor = twin if twin.get("area") is not None else l
        for m in (l, twin):
            m["area"] = donor.get("area")
            if m.get("type") == "flat":
                m["rooms"] = donor.get("rooms")
        linked += 1
    return linked


def _union_twins(clusters):
    """Fold clusters that hold two halves of the same ``_twin`` into one."""
    home, out = {}, []
    for cluster in clusters:
        keys = {m["_twin"] for m in cluster if m.get("_twin")}
        target = next((home[k] for k in keys if k in home), None)
        if target is None:
            out.append(cluster)
            target = cluster
        else:
            target.extend(cluster)
        for k in keys:
            home[k] = target
    return out


def _cross_size_unify(listings):
    """Same town + same asking price + same gallery = same property, even when
    the declared area differs between portals (agents mix usable m2 with total
    m2 — e.g. 204 m2 on Otodom vs 280 m2 on n-online for one house). The
    size-first grouping would never compare their photos, so unify the areas
    up front: every photo-cluster member inherits the preferred source's size.
    Developments are excluded (same price + photos across sizes there means
    different unit types, which must stay apart)."""
    buckets = defaultdict(list)
    for l in listings:
        loc = (l.get("locality") or "").strip().lower()
        if l.get("price") and loc and l.get("phashes") and not is_development(l):
            buckets[(l.get("type"), loc, l["price"])].append(l)
    for members in buckets.values():
        if len(members) < 2:
            continue
        for cluster in _photo_clusters(members):
            sizes = {round(m["area"], 2) for m in cluster if m.get("area") is not None}
            if len(cluster) < 2 or len(sizes) <= 1:
                continue
            # pick the size donor among members that HAVE an area — otherwise an
            # area-less best-ranked ad would wipe every member's area
            best = sorted((m for m in cluster if m.get("area") is not None), key=_rank)[0]
            for m in cluster:
                m["area"] = best.get("area")
                if m.get("type") == "flat":
                    m["rooms"] = best.get("rooms")
    return listings


def dedupe(listings, allow_heuristic_fallback=False):
    """Build properties, optionally allowing size/price merges without photos.

    ``allow_heuristic_fallback`` exists for the explicit ``RENTGEN_PHOTOS=0``
    mode. Production photo runs set it false: a failed or deferred photo fetch
    must not silently turn into weaker merge evidence.
    """
    link_twins(listings)
    _cross_size_unify(listings)
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
    # Size-less ads normally can't be matched to anything — except a twin pair,
    # whose portal id identifies it without an area at all.
    for cluster in _union_twins([[l] for l in loners]):
        prop = _build(cluster)
        if is_development(cluster[0]):
            prop["development"] = True
        properties.append(prop)
    for members in groups.values():
        if len(members) == 1:
            prop = _build(members)
            if is_development(members[0]):
                prop["development"] = True
            properties.append(prop)
        elif any(m.get("phashes") for m in members):
            # photos available -> merge only ads whose hashes match
            for cluster in _union_twins(_photo_clusters(members)):
                if _cluster_is_development(cluster):
                    properties.extend(_build_dev(cluster))
                else:
                    properties.append(_build(cluster))
        elif not allow_heuristic_fallback:
            # Photo mode was requested but this whole size group remains
            # unresolved. Keep every ad separate rather than letting a CDN or
            # cache failure authorize the loose size/price heuristic. Exact
            # gratka↔morizon portal-ID twins remain safe to union.
            for cluster in _union_twins([[member] for member in members]):
                prop = _build(cluster)
                if any(is_development(member) for member in cluster):
                    prop["development"] = True
                properties.append(prop)
        else:
            # no photo data -> fall back to the size + price-spread heuristic
            dev = _cluster_is_development(members)
            for cluster in _union_twins(_split_by_price(members)):
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
            others = [m for m in members if m.get("url") != p.get("url")
                      and compatible(p, m)]
            if not others:
                continue
            p["relisted"] = True
            p["also_listed"] = [{"price": o.get("price"), "url": o.get("url"),
                                 "source": o.get("source"), "first_seen": o.get("first_seen")}
                                for o in others]
            cheaper = [o.get("price") for o in others if o.get("price") is not None]
            # a genuine earlier price from history beats "what the concurrent
            # duplicate asks right now" — don't clobber it
            if cheaper and p.get("prev_price") is None:
                p["prev_price"] = min(cheaper)
    return properties
