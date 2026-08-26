"""morizon.pl scraper — region-wide sale listings (RENTGEN_REGION).

morizon uses the same server-rendered ``data-cy`` card frontend as gratka (same
media group), so the parsing mirrors the gratka scraper.
"""
from __future__ import annotations

import os
import re
import time

import requests
from bs4 import BeautifulSoup

from . import bands, coverage, photomatch
from .normalize import location_parts, stated_total, take_unseen, to_float, to_int

BASE = "https://www.morizon.pl"
# Whole-voivodeship search by default; override with RENTGEN_REGION.
REGION = os.environ.get("RENTGEN_REGION", "slaskie")
SEARCH = {
    "house": [f"https://www.morizon.pl/domy/{REGION}/"],
    "flat": [f"https://www.morizon.pl/mieszkania/{REGION}/"],
}
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8",
}
# Same 200-page 404 wall as gratka — same frontend, same database.
PORTAL_PAGE_WALL = 200


def _text(card, cy):
    el = card.select_one(f'[data-cy="{cy}"]')
    return el.get_text(" ", strip=True) if el else None


def _first_price(text):
    if not text:
        return None
    return to_int(text.split("zł")[0])


def _locality(location):
    """City = the broadest (last) breadcrumb part of 'street, district, city,
    voivodeship', e.g. 'Tarnogórska, Szobiszowice, Gliwice, śląskie' -> 'Gliwice'
    (taking the first segment stored street names like 'Tarnogórska' as fake towns).

    Nothing is folded by prefix — see the note in gratka._locality()."""
    parts = location_parts(location)
    if not parts:
        return None
    return parts[-1] or None


def _district(location):
    """The narrower part(s) before the city, e.g. 'Tarnogórska, Szobiszowice'."""
    inner = location_parts(location)[:-1]
    return ", ".join(inner) if inner else None


def _date(text):
    m = re.search(r"(\d{4})\.(\d{2})\.(\d{2})", text or "")
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


def _image(card):
    img = (card.select_one('[data-cy="gallerySliderImgThumbnail"]')
           or card.select_one("img.gallery-slider__img"))
    if img is None:
        return None
    src = img.get("src") or ""
    return src if src.startswith("http") and not src.endswith(".svg") else None


def parse_cards(html: str, typ: str):
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for card in soup.select('[data-cy="card"]'):
        a = card.select_one('a[data-cy="propertyUrl"]') or card.select_one("a[href]")
        href = a.get("href") if a else None
        if not href:
            continue
        url = href if href.startswith("http") else BASE + href
        m_id = re.search(r"mzn(\d+)", url)
        loc = _text(card, "propertyCardLocation")
        image = _image(card)
        out.append({
            "source": "morizon",
            "source_id": m_id.group(1) if m_id else url,
            # morizon and gratka are one database: the card thumbnail is a
            # base64-wrapped `d-gr.cdngr.pl` origin carrying GRATKA's ad id, so
            # the duplicate is provable here, off the search page, with no
            # detail fetch and no photo hashing (see photomatch.gratka_ad_id and
            # normalize.link_twins). Absent on the `gr-col` id space, which
            # still needs photos.
            "gratka_id": photomatch.gratka_ad_id(image),
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
            "image": image,
            "created": _date(_text(card, "descriptionAddedAtDate")),
            "also_on": [],
        })
    return out


def _walk(base, typ, tag, max_pages, delay, session, log, seen, out, extra=""):
    """Page through one search (optionally price-banded). Returns its cov row."""
    page = 1
    got = 0
    served = 0            # cards the portal handed over, before OUR dedupe
    served_keys = set()
    kept_keys = set()
    total = None
    total_min = False
    stopped = coverage.OK
    error = None
    http_status = None
    while True:
        if page > max_pages:
            stopped = coverage.OUR_CAP   # morizon 404s past its last page
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
        except Exception as exc:  # keep what we have, move on
            log(f"  morizon {typ}/{tag} page {page} error: {exc}")
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
        log(f"  morizon {typ}/{tag} page {page}: +{len(batch)}")
        # Stop on an empty PAGE, not an empty batch. A price band re-sorts the
        # results, so its first pages are often ads the unbanded pass already
        # took while later pages hold new ones — breaking on "nothing new here"
        # would silently abandon the band at page 1.
        if not cards:
            break
        page += 1
        time.sleep(delay)
    # Same 200-page wall as gratka (bisected 2026-08-08), same blind spot: the
    # 404 looks like the end of the results. morizon's own count is phrased
    # "ponad 9000" and rounds to whole thousands, so it is a lower bound —
    # which is still enough to prove truncation. See the note in gratka._walk
    # for why a banded search is judged on pages rather than on that total, and
    # for what `served` is doing on the row.
    if stopped == coverage.OK and page >= PORTAL_PAGE_WALL:
        stopped = coverage.PORTAL_CAP
    elif stopped == coverage.OK and not extra and coverage.short_of_total(got, total):
        stopped = coverage.PORTAL_CAP
    return coverage.row("morizon", typ, tag, max(page, 0), got, stopped,
                        portal_total=total, total_is_min=total_min,
                        served=served, served_keys=served_keys,
                        kept_keys=kept_keys, error=error,
                        http_status=http_status)


def scrape(max_pages: int = 50, delay: float = 0.7, session=None, log=print,
           types=("house", "flat"), banded=True):
    session = session or requests.Session()
    out = []
    cov = []
    # One retry budget for the whole portal — see bands.Pacer.
    pacer = bands.Pacer("morizon", delay=delay, log=log)
    for typ, bases in SEARCH.items():
        if typ not in types:
            continue
        seen = set()
        for base in bases:
            tag = base.rstrip("/").split("/")[-1]
            pacer.pause()
            # a refused first search leaves nothing to subdivide, so it gets
            # the same one bounded retry a band does
            row = pacer.attempt(tag, lambda: _walk(base, typ, tag, max_pages,
                                                   delay, session, log, seen, out))
            row["role"] = coverage.PARENT
            cov.append(row)
            if not banded or not bands.overflows(row, "morizon"):
                continue
            log(f"  morizon {typ}/{tag}: {row.get('portal_total')} ads stated, "
                f"past the 200-page wall — subdividing by price")
            rows, seeds = bands.subdivide(
                "morizon",
                lambda lo, hi, btag: _walk(base, typ, f"{tag}/{btag}", max_pages,
                                           delay, session, log, seen, out,
                                           bands.qs("morizon", lo, hi)),
                log=log, pacer=pacer)
            cov.extend(rows)
            totals_ok = bands.check_totals(
                "morizon", typ, row.get("portal_total"), seeds, log=log)
            bands.record_partition(row, seeds, totals_ok)
    scrape.last_coverage = cov
    return out
