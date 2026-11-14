"""gratka.pl scraper — region-wide sale listings (RENTGEN_REGION).

gratka hydrates its Nuxt state client-side (``window.__NUXT__`` is empty) but
renders result cards server-side with stable ``data-cy`` hooks, parsed here with
BeautifulSoup. `SEARCH` keeps a list of base URLs per type so a region can be
split into several searches — needed once the pagination cap forces per-powiat
subdivision (see TODO.md, whole-Poland plan).
"""
from __future__ import annotations

import os
import re
import time

import requests
from bs4 import BeautifulSoup

from . import bands, coverage
from .normalize import location_parts, stated_total, take_unseen, to_float, to_int
from .regions import portal_slug

BASE = "https://gratka.pl"
REGION = os.environ.get("RENTGEN_REGION", "slaskie")
PORTAL_REGION = portal_slug(REGION, "gratka")
SEARCH = {
    "house": [f"https://gratka.pl/nieruchomosci/domy/{PORTAL_REGION}"],
    "flat": [f"https://gratka.pl/nieruchomosci/mieszkania/{PORTAL_REGION}"],
}
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8",
}
PORTAL_PAGE_WALL = 200

def _text(card, cy):
    el = card.select_one(f'[data-cy="{cy}"]')
    return el.get_text(" ", strip=True) if el else None

def _first_price(text):
    if not text:
        return None
    return to_int(text.split("zł")[0])

def _locality(location):
    """The city = the broadest (last) part of 'street, district, city, voivodeship',
    e.g. 'Szafirowa, Stare Gliwice, Gliwice, śląskie' -> 'Gliwice'. Gratka/Morizon
    order the breadcrumb specific->general, so the city is the last segment after
    the voivodeship is dropped (taking the first stored street names like
    'Szafirowa' as fake towns).

    Nothing is folded by prefix. A `startswith("Gliwice")` special case lived
    here from the Gliwice-city days; voivodeship-wide it never fires (no such
    locality exists in the data), and generalising it would corrupt real
    villages — 'Żarki-Letnisko' is not 'Żarki', 'Góra Włodowska' is not 'Góra'.
    """
    parts = location_parts(location)
    if not parts:
        return None
    return parts[-1] or None

def _district(location):
    """The narrower part(s) before the city, e.g. 'Szafirowa, Stare Gliwice'."""
    inner = location_parts(location)[:-1]
    return ", ".join(inner) if inner else None

def _date(text):
    m = re.search(r"(\d{4})\.(\d{2})\.(\d{2})", text or "")
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None

def _image(card):
    img = (card.select_one('[data-cy="gallerySliderImgThumbnail"]')
           or card.select_one("img.gallery-slider__img"))
    if img is None:
        for cand in card.select("img"):
            v = cand.get("src") or ""
            if v.startswith("http") and not v.endswith(".svg") and "nuxt-assets" not in v:
                img = cand
                break
    if img is None:
        return None
    src = img.get("src") or ""
    if src.startswith("http") and not src.endswith(".svg"):
        return src
    srcset = img.get("srcset") or img.get("data-srcset") or ""
    first = srcset.split()[0] if srcset else ""
    return first if first.startswith("http") else None

def parse_cards(html: str, typ: str):
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for card in soup.select('[data-cy="card"]'):
        a = card.select_one('a[data-cy="propertyUrl"]') or card.select_one("a[href]")
        href = a.get("href") if a else None
        if not href:
            continue
        url = href if href.startswith("http") else BASE + href
        m_id = re.search(r"/(\d+)(?:$|[/?])", url)
        loc = _text(card, "propertyCardLocation")
        out.append({
            "source": "gratka",
            "source_id": m_id.group(1) if m_id else url,
            "url": url,
            "title": _text(card, "propertyCardTitle"),
            "type": typ,
            "price": _first_price(_text(card, "cardPropertyOfferPrice")
                                  or _text(card, "propertyCardPrice")),
            "area": to_float((_text(card, "cardPropertyInfoArea") or "").split("m")[0]),
            "price_per_m2": _first_price(_text(card, "offerPricePerM2")),
            "rooms": to_int(_text(card, "cardPropertyInfoRooms")),
            "plot_area": None,
            "floor": None,
            "locality": _locality(loc),
            "district": _district(loc),
            "street": None,
            "is_private": None,
            "agency": None,
            "image": _image(card),
            "created": _date(_text(card, "descriptionAddedAtDate")),
            "also_on": [],
        })
    return out

def _walk(base, typ, tag, max_pages, delay, session, log, seen, out, extra=""):
    """Page through one search (optionally price-banded). Returns its cov row."""
    page = 1
    got = 0
    served = 0
    served_keys = set()
    kept_keys = set()
    total = None
    total_min = False
    stopped = coverage.OK
    error = None
    http_status = None
    while True:
        if page > max_pages:
            stopped = coverage.OUR_CAP
            page -= 1
            break
        query = "&".join(q for q in (f"page={page}" if page > 1 else "", extra) if q)
        url = f"{base}?{query}" if query else base
        try:
            r = session.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 404:
                page -= 1
                break
            r.raise_for_status()
            if total is None:
                total, total_min = stated_total(r.text)
            cards = parse_cards(r.text, typ)
            batch = take_unseen(cards, seen)
        except Exception as exc:
            log(f"  gratka {typ}/{tag} page {page} error: {exc}")
            stopped = coverage.ERROR
            error, http_status = coverage.error_details(exc)
            break
        served_keys.update(coverage.listing_key(
            typ, c.get("source_id") or c.get("url")) for c in cards)
        kept_keys.update(coverage.listing_key(
            typ, c.get("source_id") or c.get("url")) for c in cards)
        out.extend(batch)
        got += len(batch)
        served += len(cards)
        log(f"  gratka {typ}/{tag} page {page}: +{len(batch)}")
        if not cards:
            break
        page += 1
        time.sleep(delay)
    if stopped == coverage.OK and page >= PORTAL_PAGE_WALL:
        stopped = coverage.PORTAL_CAP
    elif stopped == coverage.OK and not extra and coverage.short_of_total(got, total):
        stopped = coverage.PORTAL_CAP
    return coverage.row("gratka", typ, tag, max(page, 0), got, stopped,
                        portal_total=total, total_is_min=total_min,
                        served=served, served_keys=served_keys,
                        kept_keys=kept_keys, error=error,
                        http_status=http_status)

def scrape(max_pages: int = 50, delay: float = 0.7, session=None, log=print,
           types=("house", "flat"), banded=True):
    session = session or requests.Session()
    out = []
    cov = []
    pacer = bands.Pacer("gratka", delay=delay, log=log)
    for typ, bases in SEARCH.items():
        if typ not in types:
            continue
        seen = set()
        for base in bases:
            tag = base.rstrip("/").split("/")[-1]
            pacer.pause()
            row = pacer.attempt(tag, lambda: _walk(base, typ, tag, max_pages,
                                                   delay, session, log, seen, out))
            row["role"] = coverage.PARENT
            cov.append(row)
            if not banded or not bands.overflows(row, "gratka"):
                continue
            log(f"  gratka {typ}/{tag}: {row.get('portal_total')} ads stated, "
                f"past the 200-page wall — subdividing by price")
            rows, seeds = bands.subdivide(
                "gratka",
                lambda lo, hi, btag: _walk(base, typ, f"{tag}/{btag}", max_pages,
                                           delay, session, log, seen, out,
                                           bands.qs("gratka", lo, hi)),
                log=log, pacer=pacer)
            cov.extend(rows)
            totals_ok = bands.check_totals(
                "gratka", typ, row.get("portal_total"), seeds, log=log)
            bands.record_partition(row, seeds, totals_ok)
    scrape.last_coverage = cov
    return out
