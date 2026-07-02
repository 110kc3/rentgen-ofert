"""OLX scraper for Gliwice sale listings.

OLX embeds its search state in a `window.__PRERENDERED_STATE__ = "..."`
assignment where the value is a JSON string that has itself been JSON-encoded
(double-encoded), so it is decoded twice.

Ads that OLX syndicates from a partner portal (notably Otodom, partner code
``otodom_pl``) are skipped here because they are already collected directly
from Otodom - this removes the largest source of cross-portal duplicates.
"""
from __future__ import annotations

import json
import os
import re
import time

import requests

from .normalize import olx_rooms, to_float, to_int

# Whole-voivodeship search by default; override with RENTGEN_REGION.
REGION = os.environ.get("RENTGEN_REGION", "slaskie")
SEARCH = {
    "house": f"https://www.olx.pl/nieruchomosci/domy/sprzedaz/{REGION}/",
    "flat": f"https://www.olx.pl/nieruchomosci/mieszkania/sprzedaz/{REGION}/",
}
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
_STATE = re.compile(r'__PRERENDERED_STATE__\s*=\s*"(.*?)";', re.S)


def extract_state(html: str) -> dict:
    m = _STATE.search(html)
    if not m:
        raise ValueError("OLX: __PRERENDERED_STATE__ not found (layout changed?)")
    return json.loads(json.loads('"' + m.group(1) + '"'))


def _params(ad) -> dict:
    return {p["key"]: (p.get("normalizedValue") or p.get("value"))
            for p in ad.get("params", [])}


def parse_ads(ads, typ: str):
    out = []
    for ad in ads:
        partner = (ad.get("partner") or {}).get("code")
        if partner or ad.get("externalUrl"):
            continue  # syndicated (e.g. Otodom) -> collected at the source
        price = ((ad.get("price") or {}).get("regularPrice") or {})
        if not price.get("value"):
            continue  # "free"/"exchange"/price-on-request ads
        pm = _params(ad)
        loc = ad.get("location") or {}
        photos = ad.get("photos") or []
        user = ad.get("user") or {}
        is_business = bool(ad.get("isBusiness"))
        out.append({
            "source": "olx",
            "source_id": str(ad.get("id")),
            "url": ad.get("url"),
            "title": ad.get("title"),
            "type": typ,
            "price": price.get("value"),
            "area": to_float(pm.get("m")),
            "price_per_m2": to_int(pm.get("price_per_m")),
            "rooms": olx_rooms(pm.get("rooms")),
            "plot_area": to_float(pm.get("area")) if typ == "house" else None,
            "floor": pm.get("floor_select"),
            "locality": loc.get("cityName"),
            "district": loc.get("districtName"),
            "street": None,
            "is_private": not is_business,
            "market": (str(pm.get("market")).lower() if pm.get("market") else None),
            "agency": user.get("name") if is_business else None,
            "image": photos[0] if photos else None,
            "created": ad.get("lastRefreshTime") or ad.get("createdTime"),
            "also_on": [],
        })
    return out


def scrape(max_pages: int = 50, delay: float = 0.7, session=None, log=print,
           types=("house", "flat")):
    session = session or requests.Session()
    out = []
    for typ, base_url in SEARCH.items():
        if typ not in types:
            continue
        page = 1
        while page <= max_pages:
            url = f"{base_url}?page={page}"
            try:
                r = session.get(url, headers=HEADERS, timeout=30)
                r.raise_for_status()
                state = extract_state(r.text)
                listing = state["listing"]["listing"]
            except Exception as exc:  # keep what we have, stop this category
                log(f"  olx {typ} page {page} error: {exc}")
                break
            batch = parse_ads(listing.get("ads", []), typ)
            out.extend(batch)
            total_pages = listing.get("totalPages", 1) or 1
            log(f"  olx {typ} page {page}/{min(total_pages, max_pages)}: +{len(batch)}")
            if page >= min(total_pages, max_pages) or not listing.get("ads"):
                break
            page += 1
            time.sleep(delay)
    return out
