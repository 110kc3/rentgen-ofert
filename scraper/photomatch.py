"""Perceptual photo matching to confirm two listings are the same property.

The cover photo alone is unreliable (each portal picks a different one), so we
fetch each listing's detail page, collect a few gallery image URLs, and compute
a 256-bit dHash per image. Two listings are "the same" when the closest pair of
their gallery hashes is within PHOTO_THRESHOLD. On ground-truth cross-portal
pairs the closest pair scores ~16-27, while different properties score ~115, so
the threshold has a wide safety margin.

Only used for listings that share an exact size with another (the ambiguous
ones); everything else never needs a detail fetch.
"""
from __future__ import annotations

import base64
import io
import json
import re
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import requests
from PIL import Image

MAX_IMAGES = 5          # gallery images hashed per listing
PHOTO_THRESHOLD = 40    # max dHash hamming for "same photo"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8",
}


def dhash(image_bytes, size: int = 16) -> int:
    """256-bit difference hash (16x16) of an image."""
    im = Image.open(io.BytesIO(image_bytes)).convert("L").resize((size + 1, size))
    px = list(im.getdata())
    h, bit = 0, 0
    for row in range(size):
        base = row * (size + 1)
        for col in range(size):
            if px[base + col] < px[base + col + 1]:
                h |= 1 << bit
            bit += 1
    return h


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


# ---- per-portal gallery extraction -----------------------------------------

def _otodom(html):
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return []
    ad = json.loads(m.group(1))["props"]["pageProps"].get("ad") or {}
    return [i.get("large") or i.get("medium") for i in (ad.get("images") or []) if i]


def _olx(html):
    urls = re.findall(r'https://[a-z]+\.apollo\.olxcdn\.com:?\d*/v1/files/[^"\\\s]+', html)
    out, seen = [], set()
    for u in urls:
        fid = u.split("/files/")[-1].split("/")[0]
        if fid not in seen:
            seen.add(fid)
            out.append(u)
    return out


# ---- the gratka/morizon CDN ------------------------------------------------
#
# gratka and morizon are one database behind two frontends, and their image CDN
# says so: both serve `<host>/thumb/<base64>/<rendition>/<slug>.jpg`, where the
# base64 decodes to the SAME origin URL on `d-gr.cdngr.pl` carrying gratka's own
# ad id. Three consequences, all of them load-bearing:
#
#   1. The host moved to `img*.staticmorizon.com.pl` at some point and morizon
#      matched nothing for however long — 0 of 9 505 morizon cards in the
#      2026-08-08 run had a single hash, so morizon could never merge with
#      anything and shipped ~7 000 duplicate cards. Hence the fixtures: this
#      regex has now broken twice, and a host list is not a spec.
#   2. The five URLs a gallery shows first are the xs/s/m/l/og renditions of ONE
#      photo, so a plain first-five slice hashed one photo five times. Dedupe by
#      origin, then take one rendition each.
#   3. Blog teasers ride the same `/thumb/` path and their slug ends `.jpg` too,
#      so a host-only pattern silently hashes stock article art. Only origins
#      under `d-gr.cdngr.pl/kadry/` are listing photos.
_CDN_THUMB = re.compile(
    r'https://(?:thumbs\.cdngr\.pl|img\d*\.staticmorizon\.com\.pl|img\d*\.morizon\.pl)'
    r'/thumb/([A-Za-z0-9+/=]+)/[^"\s\\)]+')
# the origin path holds gratka's ad id: .../gr-ogl/1e/0f/48557359_1546700385.jpg
_ORIGIN_AD = re.compile(r'd-gr\.cdngr\.pl/kadry/[^?"\s]*?/gr-ogl/(?:[^/]+/)*(\d+)_\d+')
# rendition preference: hash the biggest one available for a given origin
_RENDITION_RANK = ("og_image", "3x2_l", "3x2_m", "3x2_s", "3x2_xs")


def _decode_origin(b64: str):
    """The origin URL a `/thumb/<base64>/` CDN link wraps, or None."""
    try:
        # urlsafe- and padding-tolerant: the CDN pads, but don't rely on it
        return base64.b64decode(b64 + "=" * (-len(b64) % 4)).decode("utf-8", "replace")
    except Exception:
        return None


def gratka_ad_id(url: str):
    """gratka's ad id embedded in a gratka/morizon thumb URL, or None.

    This is the cheapest merge key in the pipeline: a morizon card's *search
    page* thumbnail already carries it, so a morizon↔gratka pair is provable
    with no detail fetch and no image fetch at all. Measured on the 2026-08-08
    published data: 7 089 of the 9 472 decodable morizon thumbs resolved to a
    gratka ad we already held — every single one of the `gr-ogl` flavour.
    (The rest are `gr-col`, a different id space, and still need photo hashes.)
    """
    m = re.search(r'/thumb/([A-Za-z0-9+/=]+)/', url or "")
    if not m:
        return None
    origin = _decode_origin(m.group(1))
    hit = _ORIGIN_AD.search(origin) if origin else None
    return hit.group(1) if hit else None


def _cdn_gallery(html):
    """Listing photos from a gratka/morizon page: one URL per distinct origin."""
    by_origin = {}
    for m in _CDN_THUMB.finditer(html):
        url = m.group(0)
        origin = _decode_origin(m.group(1))
        if not origin or "d-gr.cdngr.pl/kadry/" not in origin:
            continue          # blog teaser / agency logo, not this listing
        by_origin.setdefault(origin, []).append(url)

    def best(urls):
        return min(urls, key=lambda u: next(
            (i for i, r in enumerate(_RENDITION_RANK) if f"/{r}" in u),
            len(_RENDITION_RANK)))

    return [best(urls) for urls in by_origin.values()]


_gratka = _cdn_gallery
_morizon = _cdn_gallery


_NOL_SKIP = re.compile(r'contact|logo|avatar|agent|baner|stopka|ikona|placeholder', re.I)


def _nol(html):
    urls = re.findall(r'https://i\.st-nieruchomosci-online\.pl/[^"\s]+?\.(?:jpg|jpeg|webp)', html)
    return [u for u in dict.fromkeys(urls) if not _NOL_SKIP.search(u)]


_EXTRACTORS = {"otodom": _otodom, "olx": _olx, "gratka": _gratka,
               "morizon": _morizon, "nieruchomosci-online": _nol}


def gallery_urls(listing, session) -> list:
    extractor = _EXTRACTORS.get(listing.get("source"))
    if not extractor or not listing.get("url"):
        return []
    try:
        r = session.get(listing["url"], headers=HEADERS, timeout=20)
        r.raise_for_status()
        return [u for u in extractor(r.text) if u][:MAX_IMAGES]
    except Exception:
        return []


def listing_hashes(listing, session) -> tuple:
    """(hashes, image_urls) for a listing's gallery."""
    hashes, urls = [], []
    for url in gallery_urls(listing, session):
        try:
            r = session.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            hashes.append(dhash(r.content))
            urls.append(url)
        except Exception:
            continue
    return hashes, urls


def prioritize(listings, cache=None, today=None):
    """Return ``(ordered listings, correctness-critical URL set)``.

    Photo hashes answer two different questions:

    * current ads that collide on the dedupe keys need them *now* so today's
      cards are not merged by the size/price fallback;
    * every other active or archived ad is useful only for future relist and
      lifecycle matching.

    Cold regions can exceed the wall-clock photo budget, so those queues must
    not be left in portal scrape order. Critical current collisions go first.
    Within each queue, cache hits are free, previously budget-deferred URLs are
    oldest-first, never-attempted URLs precede negative-cache retries, and the
    URL makes the order stable between runs. That last distinction matters in
    practice: the first Małopolskie pilot spent most of its 90 minutes proving
    that thousands of Otodom detail pages yielded no gallery while tens of
    thousands of never-attempted n-online ads waited behind them.
    """
    from . import cache as cachemod
    from . import normalize

    cache = cache or {"entries": {}}
    entries = cache.get("entries") or {}
    deferred = cachemod.backlog(cache)
    active = [
        listing for listing in listings
        if not listing.get("archived")
        and not listing.get("_identified_by")
        and listing.get("url")
    ]

    by_size = defaultdict(list)
    by_location_price = defaultdict(list)
    for listing in active:
        size = normalize.size_key(listing)
        if size is not None:
            by_size[size].append(listing)
        locality = (listing.get("locality") or "").strip().lower()
        if (listing.get("price") and locality
                and not normalize.is_development(listing)):
            by_location_price[
                (listing.get("type"), locality, listing["price"])
            ].append(listing)

    critical_urls = set()
    for groups in (by_size, by_location_price):
        for members in groups.values():
            if len(members) > 1:
                critical_urls.update(member["url"] for member in members)

    def fetch_state(listing):
        url = listing.get("url")
        if listing.get("_identified_by") or not url:
            return (0, "")                 # already settled / nothing to fetch
        entry = entries.get(url)
        if entry:
            if entry.get("h") or entry.get("hashes"):
                return (0, "")             # positive cache hit
            if cachemod.get(cache, url, today) is not None:
                return (0, "")             # believed recent negative hit
        if url in deferred:
            return (1, deferred[url])       # oldest budget work first
        if not entry:
            return (2, "")                 # never attempted
        return (3, "")                     # retry a prior empty response last

    def key(listing):
        url = listing.get("url") or ""
        state, first_deferred = fetch_state(listing)
        return (
            0 if url in critical_urls else 1,
            state,
            first_deferred,
            1 if listing.get("archived") else 0,
            listing.get("source") or "",
            url,
        )

    return sorted(listings, key=key), critical_urls


def attach_hashes(listings, max_workers: int = 8, session=None, log=print,
                  cache=None, today=None, budget_s=None, critical_urls=None):
    """Fetch galleries and set listing['phashes'] for each given listing.

    If a ``cache`` dict (see ``scraper.cache``) is given, listings whose URL is
    already cached reuse the stored hashes and skip the detail-page + image
    fetches - the slowest, most rate-limited part of a run. An empty result is
    written back as a *miss*, not dropped: after
    ``cache.MISS_RETRIES`` of them the ad is believed to have no photos we can
    reach and stops being fetched for a week. Before that it was re-fetched
    every run forever — 9 505 morizon detail pages per run, all returning
    nothing, all charged to the photo budget.

    ``budget_s`` bounds the wall clock of the FETCHING part: once exceeded,
    remaining un-cached listings are skipped this run (no hashes, not cached —
    picked up again next run). Cache hits are always served. This keeps a
    rate-limited portal from stretching the run past the CI job timeout.

    A listing carrying ``_identified_by`` is skipped outright and costs
    nothing: `normalize.link_twins` has already settled what it is, by portal
    id, off the search page (see there).

    ``critical_urls`` does not reorder work; pass the result of ``prioritize``.
    It labels deferred work in the returned metrics so a run can prove whether
    the correctness queue completed. The return value also carries a private
    ``deferred_urls`` list for persistence in the regional cache; callers must
    remove it before publishing the compact metrics.
    """
    from . import net
    from . import cache as cachemod
    session = session or net.session()
    deadline = time.monotonic() + budget_s if budget_s else None
    critical_urls = set(critical_urls or ())

    def work(l):
        url = l.get("url")
        if l.get("_identified_by"):
            # Already identified by portal id, so its photos would answer a
            # question nobody is asking. `_build` unions its twin's hashes onto
            # the property, so nothing downstream goes without.
            return (l, None, [], "identified")
        if cache is not None and url:
            # `[]` is a HIT meaning "known to have no photos for us", None means
            # "not cached, go fetch" — `if cached:` would conflate them and
            # re-fetch every photo-less ad forever, which is exactly the bug
            # that let morizon eat the photo budget.
            cached = cachemod.get(cache, url, today)
            if cached is not None:
                return (l, cached, cachemod.get_urls(cache, url), "cached")
        if deadline is not None and time.monotonic() > deadline:
            # None, not [] — an ad we never tried must not be written back as a
            # photo miss, or a few budget-starved runs would teach the cache
            # that half the region has no photos
            return (l, None, [], "deferred")
        hashes, img_urls = listing_hashes(l, session)
        return (l, hashes, img_urls, "fetched")

    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for l, hashes, img_urls, outcome in ex.map(work, listings):
            l["phashes"] = hashes or []
            l["photo_urls"] = img_urls
            results.append((l, hashes, img_urls, outcome))

    hits = sum(1 for _, _, _, outcome in results if outcome == "cached")
    if cache is not None and today:
        for l, hashes, img_urls, outcome in results:
            url = l.get("url")
            if not url or hashes is None:
                continue
            if outcome == "cached":
                cachemod.touch(cache, url, today)
            else:
                cachemod.put(cache, url, hashes, today, image_urls=img_urls)
    deferred_urls = [
        listing.get("url")
        for listing, _, _, outcome in results
        if outcome == "deferred" and listing.get("url")
    ]
    twinned = sum(1 for _, _, _, outcome in results
                  if outcome == "identified")
    fetched = sum(1 for _, _, _, outcome in results if outcome == "fetched")
    critical_deferred = sum(
        1 for listing, _, _, outcome in results
        if outcome == "deferred" and listing.get("url") in critical_urls
    )
    skipped = sum(1 for _, _, _, outcome in results if outcome == "deferred")
    stats = {
        "listings": len(results),
        "critical": len(critical_urls),
        "history_only": max(0, len(results) - len(critical_urls) - twinned),
        "cache_hits": hits,
        "fetched": fetched,
        "with_photos": sum(1 for l in listings if l.get("phashes")),
        "identified": twinned,
        "deferred": skipped,
        "critical_deferred": critical_deferred,
        "history_deferred": skipped - critical_deferred,
        "deferred_urls": deferred_urls,
    }
    log(f"  photo-hashed {len(results)} ambiguous listings "
        f"({stats['with_photos']} with photos; "
        f"{hits} reused from cache"
        + (f"; {twinned} identified by their twin" if twinned else "")
        + (f"; {skipped} skipped, photo budget exhausted" if skipped else "")
        + ")")
    return stats
