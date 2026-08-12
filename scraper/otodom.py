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

# How far the UNBANDED search walks when price bands are going to cover the
# same ground properly. Otodom serves roughly 320 pages per run and then
# refuses with `405 Not Allowed` — measured four times (runs 31408840562,
# 31422141701, 31468177600, 31502042693), always inside the `300k-400k` band,
# always between its pages 5 and 11. A 200-page unbanded walk spends two thirds
# of that budget re-fetching ads the bands are then sent to fetch again, and
# the bands die on what is left: seven of the nine never got past page 1, and
# otodom's kept count came out at 16 6xx in every run whether they ran or not.
# The band yields say it outright — `200k-300k page 1/35: +4`, `page 2: +0`,
# `page 3: +2` — the unbanded pass had already taken them.
#
# So the unbanded pass becomes a SCOUT: deep enough to state the total, seed
# the dedupe and pick up the priceless ads that no price filter can return,
# then it stands aside. The bands partition the whole price line, which is what
# they were built for, and they get the page budget to do it with.
SCOUT_PAGES = 12
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


def _walk(path, typ, tag, max_pages, delay, session, log, seen, out, extra="",
          scout_pages=None):
    """Page through one search (optionally price-banded). Returns its cov row.

    ``scout_pages`` caps an unbanded search that bands are about to subdivide
    (see SCOUT_PAGES). It only bites once the portal has stated a total past
    its serving window — the same question `bands.overflows` asks, asked one
    page in — so a search that needs no bands still walks to ``max_pages``.
    """
    page = 1
    got = 0
    served = 0        # ads Otodom handed over, before the INVESTMENT filter
    total_pages = None
    total_ads = None
    stopped = coverage.OK
    scouted = False
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
        if (scout_pages and page >= scout_pages and total_ads
                and total_ads > bands.WINDOW["otodom"]):
            # Past the window, so `overflows` will subdivide this search no
            # matter how far it walks. Stop and let it: every further page here
            # is a page the bands will not get.
            stopped, scouted = coverage.OUR_CAP, True
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
                        served=served, scout=scouted)


def scrape(max_pages: int = 50, delay: float = 0.7, session=None, log=print,
           types=("house", "flat"), banded=True):
    session = session or requests.Session()
    out = []
    cov = []
    # One pacer for the whole portal: the unbanded searches and every band
    # share its retry budget, so a refusing Otodom costs minutes, not an hour.
    pacer = bands.Pacer("otodom", delay=delay, log=log)
    for typ, path in SEARCH.items():
        if typ not in types:
            continue
        seen = set()
        pacer.pause()
        # A refused FIRST search loses the whole type — `overflows` will not
        # subdivide an error row (rightly: a filtered search fails the same
        # way), so there are no bands to fall back on. It gets the same one
        # bounded retry a band does.
        row = pacer.attempt(typ, lambda: _walk(path, typ, REGION, max_pages,
                                               delay, session, log, seen, out,
                                               scout_pages=SCOUT_PAGES if banded
                                               else None))
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
            log=log, pacer=pacer)
        cov.extend(rows)
        bands.check_totals("otodom", typ, row.get("portal_total"), seeds, log=log)
    scrape.last_coverage = cov
    return out
