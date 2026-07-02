"""Otodom scraper for Gliwice sale listings.

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


def scrape(max_pages: int = 50, delay: float = 0.7, session=None, log=print,
           types=("house", "flat")):
    session = session or requests.Session()
    out = []
    for typ, path in SEARCH.items():
        if typ not in types:
            continue
        page = 1
        while page <= max_pages:
            url = f"{BASE}{path}?page={page}"
            try:
                r = session.get(url, headers=HEADERS, timeout=30)
                r.raise_for_status()
                sa = extract_search_ads(r.text)
            except Exception as exc:  # keep what we have, stop this category
                log(f"  otodom {typ} page {page} error: {exc}")
                break
            batch = parse_items(sa.get("items", []), typ)
            out.extend(batch)
            total_pages = (sa.get("pagination") or {}).get("totalPages", 1) or 1
            log(f"  otodom {typ} page {page}/{min(total_pages, max_pages)}: +{len(batch)}")
            if page >= min(total_pages, max_pages) or not batch:
                break
            page += 1
            time.sleep(delay)
    return out
