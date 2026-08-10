"""OLX scraper — region-wide sale listings (RENTGEN_REGION).

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

from . import bands, coverage
from .normalize import olx_rooms, to_float, to_int

# Whole-voivodeship search by default; override with RENTGEN_REGION.
REGION = os.environ.get("RENTGEN_REGION", "slaskie")
PATHS = {"house": "domy", "flat": "mieszkania"}


def search_url(typ: str, where: str) -> str:
    """The location is one slug in a fixed path position, so the same builder
    makes a region search and a town search — which is what subdivision needs.
    Verified on the sibling portals reachable from a dev machine:
    `gratka.pl/nieruchomosci/domy/gliwice` and `morizon.pl/domy/gliwice/` both
    answer with that town's listings from the region URL's slug position."""
    return f"https://www.olx.pl/nieruchomosci/{PATHS[typ]}/sprzedaz/{where}/"


SEARCH = {typ: search_url(typ, REGION) for typ in PATHS}

# OLX stops paginating long before it runs out of ads — the region search dies
# at page 25 whatever `totalPages` claims. That is not our cap and no amount of
# RENTGEN_MAX_PAGES fixes it; the only way to see the rest is to ask narrower
# questions, so an overflowing search is re-run per town and merged.
HARD_PAGE_CAP = 25
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
# escape-aware: the state is a JSON-encoded string, so a `\";` sequence inside it
# (an escaped quote followed by a semicolon in some ad text) must not end the match
_STATE = re.compile(r'__PRERENDERED_STATE__\s*=\s*"((?:[^"\\]|\\.)*)";', re.S)


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


def _walk(base_url, typ, tag, max_pages, delay, session, log, seen, out, extra=""):
    """Page through one search (optionally price-banded). Returns its cov row."""
    page = 1
    got = 0
    served = 0             # ads OLX handed over, before our own filtering
    total_pages = None
    visible = None          # ads OLX says match the search   (5 503 for śląskie flats)
    servable = None         # ads OLX will actually hand over (1 000 — its cap)
    stopped = coverage.OK
    while page <= max_pages:
        url = f"{base_url}?page={page}" + (f"&{extra}" if extra else "")
        try:
            r = session.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            state = extract_state(r.text)
            listing = state["listing"]["listing"]
        except Exception as exc:  # keep what we have, stop this search
            log(f"  olx {typ}/{tag} page {page} error: {exc}")
            stopped = coverage.ERROR
            break
        ads = listing.get("ads", [])
        served += len(ads)
        batch = [a for a in parse_ads(ads, typ) if a["url"] not in seen]
        for a in batch:
            seen.add(a["url"])
        out.extend(batch)
        got += len(batch)
        total_pages = listing.get("totalPages", 1) or 1
        visible = listing.get("visibleElements") or visible
        servable = listing.get("totalElements") or servable
        log(f"  olx {typ}/{tag} page {page}/{min(total_pages, max_pages)}: +{len(batch)}")
        if not ads:
            # An empty page is how OLX enforces its own limit: it keeps claiming
            # `totalPages` in the hundreds and just stops serving ads. Running
            # out for real means we reached the last page it claimed.
            page -= 1                     # the empty page held nothing
            # ...but an empty FIRST page with nothing matching at all is simply
            # an empty search — a village with no flats, a price band nothing
            # falls into. `totalPages` defaults to 1 there, so `1 > 0` used to
            # call it a refusal, `bands.overflows` read that as overflow, and
            # every empty half was bisected again to MAX_DEPTH. That was 1 890
            # of run 31367424054's 1 948 warnings and ~110 of OLX's 144 scrape
            # minutes, spent asking Kozy for its 1.4M flats. A real refusal
            # still states `visibleElements`, which is what tells them apart.
            if total_pages > page and not (page == 0 and not visible):
                stopped = coverage.PORTAL_CAP
            break
        if page >= min(total_pages, max_pages):
            if total_pages > max_pages:
                stopped = coverage.OUR_CAP
            break
        page += 1
        time.sleep(delay)
    # The cap OLX actually enforces is stated, not hit: for a region search it
    # answers `visibleElements: 5503` (ads matching) with `totalElements: 1000`
    # and `totalPages: 25` (ads it will serve). Walking those 25 pages therefore
    # looks like a completed search — which is why śląskie yielded 470 listings
    # and the town subdivision below never once fired. Measured 2026-08-08.
    if stopped == coverage.OK and visible and servable and visible > servable:
        stopped = coverage.PORTAL_CAP
    return coverage.row("olx", typ, tag, page, got, stopped,
                        portal_pages=total_pages, portal_total=visible,
                        served=served)


def scrape(max_pages: int = 50, delay: float = 0.7, session=None, log=print,
           types=("house", "flat"), towns=None, banded=True):
    """`towns`: {slug: display} used ONLY to subdivide a search that OLX refused
    to paginate. Subdivision is additive — the region results are kept and the
    per-town results merged into them by URL — so a wrong town slug costs one
    request and can never lose a listing we already had."""
    session = session or requests.Session()
    out = []
    cov = []
    for typ in PATHS:
        if typ not in types:
            continue
        seen = set()
        row = _walk(SEARCH[typ], typ, REGION, max_pages, delay, session, log, seen, out)
        cov.append(row)
        if row["stopped"] != coverage.PORTAL_CAP:
            continue
        # Two independent axes, and OLX needs both: towns cut the region into
        # ~60 pieces but a big city's own search hits the same 1 000-ad cap, and
        # price cuts every one of them further. Both are additive into `seen`.
        if towns:
            log(f"  olx {typ}: region search capped at page {row['pages']} of "
                f"{row.get('portal_pages')} — subdividing into {len(towns)} towns")
        for slug in (towns or {}):
            town_row = _walk(search_url(typ, slug), typ, slug, max_pages,
                             delay, session, log, seen, out)
            cov.append(town_row)
            time.sleep(delay)
            if banded and bands.overflows(town_row, "olx"):
                rows, _ = bands.subdivide(
                    "olx",
                    lambda lo, hi, btag, s=slug: _walk(
                        search_url(typ, s), typ, f"{s}/{btag}", max_pages, delay,
                        session, log, seen, out, bands.qs("olx", lo, hi)),
                    log=log)
                cov.extend(rows)
        if banded:
            # …and band the region search itself, so a region whose town list is
            # empty (a brand-new one) still gets past the cap.
            rows, seeds = bands.subdivide(
                "olx",
                lambda lo, hi, btag: _walk(SEARCH[typ], typ, btag, max_pages,
                                           delay, session, log, seen, out,
                                           bands.qs("olx", lo, hi)),
                log=log)
            cov.extend(rows)
            bands.check_totals("olx", typ, row.get("portal_total"), seeds, log=log)
    scrape.last_coverage = cov
    return out
