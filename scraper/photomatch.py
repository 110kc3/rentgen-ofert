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

import io
import json
import re
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


def _gratka(html):
    return list(dict.fromkeys(re.findall(r'https://thumbs\.cdngr\.pl/thumb/[^"\s]+?\.jpg', html)))


_NOL_SKIP = re.compile(r'contact|logo|avatar|agent|baner|stopka|ikona|placeholder', re.I)


def _nol(html):
    urls = re.findall(r'https://i\.st-nieruchomosci-online\.pl/[^"\s]+?\.(?:jpg|jpeg|webp)', html)
    return [u for u in dict.fromkeys(urls) if not _NOL_SKIP.search(u)]


_EXTRACTORS = {"otodom": _otodom, "olx": _olx, "gratka": _gratka,
               "nieruchomosci-online": _nol}


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


def listing_hashes(listing, session) -> list:
    out = []
    for url in gallery_urls(listing, session):
        try:
            r = session.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            out.append(dhash(r.content))
        except Exception:
            continue
    return out


def attach_hashes(listings, max_workers: int = 8, session=None, log=print,
                  cache=None, today=None):
    """Fetch galleries and set listing['phashes'] for each given listing.

    If a ``cache`` dict (see ``scraper.cache``) is given, listings whose URL is
    already cached reuse the stored hashes and skip the detail-page + image
    fetches - the slowest, most rate-limited part of a run. Only successful,
    non-empty results are written back, so a transient fetch failure is retried
    next run instead of being cached as "no photos".
    """
    from . import net
    from . import cache as cachemod
    session = session or net.session()

    def work(l):
        url = l.get("url")
        if cache is not None and url:
            cached = cachemod.get(cache, url)
            if cached:
                return (l, cached, True)
        return (l, listing_hashes(l, session), False)

    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for l, hashes, was_cached in ex.map(work, listings):
            l["phashes"] = hashes
            results.append((l, hashes, was_cached))

    hits = sum(1 for _, _, c in results if c)
    if cache is not None and today:
        for l, hashes, was_cached in results:
            url = l.get("url")
            if not url:
                continue
            if was_cached:
                cachemod.touch(cache, url, today)
            else:
                cachemod.put(cache, url, hashes, today)  # no-ops on empty
    log(f"  photo-hashed {len(results)} ambiguous listings "
        f"({sum(1 for l in listings if l.get('phashes'))} with photos; "
        f"{hits} reused from cache)")
