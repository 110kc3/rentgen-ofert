"""Otodom scraper — region-wide sale listings (RENTGEN_REGION).

Otodom is a Next.js app that ships the full search result set inside a
`<script id="__NEXT_DATA__">` JSON blob in the initial HTML, so no headless
browser is needed - a plain GET + JSON parse is enough.
"""
from __future__ import annotations

import json
import os
import re
import time

import requests

from . import bands, coverage
from .normalize import otodom_rooms, to_int

BASE = "https://www.otodom.pl"
# Whole-voivodeship search by default. Override with RENTGEN_REGION (an Otodom
# region slug such as "slaskie" or "malopolskie").
REGION = os.environ.get("RENTGEN_REGION", "slaskie")
SEARCH = {
    "house": f"/pl/wyniki/sprzedaz/dom/{REGION}",
    "flat": f"/pl/wyniki/sprzedaz/mieszkanie/{REGION}",
}
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
# Otodom honours &limit: 72 is the largest it serves and halves the request
# count on the biggest portal (515 pages -> 258 for śląskie flats, verified).
PAGE_SIZE = 72
_NEXT = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)


def extract_search_ads(html: str) -> dict:
    """Pull the searchAds object out of a result page's __NEXT_DATA__."""
    m = _NEXT.search(html)
    if not m:
        raise ValueError("Otodom: __NEXT_DATA__ not found (layout changed?)")
    data = json.loads(m.group(1))
    return data["props"]["pageProps"]["data"]["searchAds"]


def parse_items(items, typ: str):
    """Turn raw Otodom ad dicts into normalized listing dicts."""
    out = []
    for it in items:
        estate = it.get("estate")
        if estate not in ("HOUSE", "FLAT"):  # skip INVESTMENT bundles etc.
            continue
        loc = (it.get("location") or {}).get("address") or {}
        price = it.get("totalPrice") or {}
        ppm = it.get("pricePerSquareMeter") or {}
        images = it.get("images") or []
        slug = it.get("slug")
        out.append({
            "source": "otodom",
            "source_id": str(it.get("id")),
            "url": f"{BASE}/pl/oferta/{slug}" if slug else None,
            "title": it.get("title"),
            "type": typ,
            "price": price.get("value"),
            "area": it.get("areaInSquareMeters"),
            "price_per_m2": ppm.get("value"),
            "rooms": otodom_rooms(it.get("roomsNumber")),
            "plot_area": it.get("terrainAreaInSquareMeters"),
            "floor": it.get("floorNumber"),
            "locality": (loc.get("city") or {}).get("name") if loc.get("city") else None,
            "district": (loc.get("district") or {}).get("name") if loc.get("district") else None,
            "street": (loc.get("street") or {}).get("name") if loc.get("street") else None,
            "is_private": it.get("isPrivateOwner"),
            # PRIMARY = new-build/developer, SECONDARY = resale
            "market": (it.get("market") or "").lower() or None,
            "agency": (it.get("agency") or {}).get("name") if it.get("agency") else None,
            "image": images[0].get("medium") or images[0].get("large") if images else None,
            "created": it.get("dateCreated"),
            "also_on": [],
        })
    return out


def _walk(path, typ, tag, max_pages, delay, session, log, seen, out, extra=""):
    """Page through one search (optionally price-banded). Returns its cov row."""
    page = 1
    got = 0
    served = 0        # ads Otodom handed over, before the INVESTMENT filter
    total_pages = None
    total_ads = None
    stopped = coverage.OK
    while page <= max_pages:
        url = f"{BASE}{path}?page={page}&limit={PAGE_SIZE}" + (f"&{extra}" if extra else "")
        try:
            r = session.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            sa = extract_search_ads(r.text)
        except Exception as exc:  # keep what we have, stop this category
            log(f"  otodom {typ}/{tag} page {page} error: {exc}")
            stopped = coverage.ERROR
            break
        items = sa.get("items") or []
        served += len(items)
        batch = [a for a in parse_items(items, typ) if a["url"] not in seen]
        for a in batch:
            seen.add(a["url"])
        out.extend(batch)
        got += len(batch)
        pg = sa.get("pagination") or {}
        total_pages = pg.get("totalPages", 1) or 1
        # `pagination.totalItems` is where Otodom states its count (18 505
        # śląskie flats on 2026-08-08). The old code read `totalResults` /
        # `count` off searchAds — neither key exists, so portal_total was
        # silently null on every coverage row it ever wrote.
        total_ads = pg.get("totalItems") or total_ads
        log(f"  otodom {typ}/{tag} page {page}/{min(total_pages, max_pages)}: +{len(batch)}")
        # stop on an empty RESULT page, not an empty parsed batch — a page of
        # nothing but INVESTMENT bundles filters to [] while more pages exist
        if not items:
            break
        if page >= min(total_pages, max_pages):
            # Otodom states its own totalPages, so we know exactly which
            # limit bit: ours (more pages exist) or the portal's end.
            stopped = (coverage.OUR_CAP if total_pages > max_pages
                       else coverage.OK)
            break
        page += 1
        time.sleep(delay)
    return coverage.row("otodom", typ, tag, page, got, stopped,
                        portal_pages=total_pages, portal_total=total_ads,
                        served=served)


def scrape(max_pages: int = 50, delay: float = 0.7, session=None, log=print,
           types=("house", "flat"), banded=True):
    session = session or requests.Session()
    out = []
    cov = []
    for typ, path in SEARCH.items():
        if typ not in types:
            continue
        seen = set()
        row = _walk(path, typ, REGION, max_pages, delay, session, log, seen, out)
        cov.append(row)
        if not banded or not bands.overflows(row, "otodom"):
            continue
        # 18 505 flats behind a window worth ~7 200: the region search can only
        # ever show a third of them, so ask by price instead. Additive — the
        # unbanded results above are kept.
        log(f"  otodom {typ}: {row.get('portal_total')} ads stated, past the "
            f"reachable window — subdividing by price")
        rows, seeds = bands.subdivide(
            "otodom",
            lambda lo, hi, tag: _walk(path, typ, tag, max_pages, delay, session,
                                      log, seen, out, bands.qs("otodom", lo, hi)),
            log=log)
        cov.extend(rows)
        bands.check_totals("otodom", typ, row.get("portal_total"), seeds, log=log)
    scrape.last_coverage = cov
    return out
