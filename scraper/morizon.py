"""morizon.pl scraper for Gliwice + powiat gliwicki sale listings.

morizon uses the same server-rendered ``data-cy`` card frontend as gratka (same
media group), so the parsing mirrors the gratka scraper.
"""
from __future__ import annotations

import os
import re
import time

import requests
from bs4 import BeautifulSoup

from .normalize import to_float, to_int

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


def _text(card, cy):
    el = card.select_one(f'[data-cy="{cy}"]')
    return el.get_text(" ", strip=True) if el else None


def _first_price(text):
    if not text:
        return None
    return to_int(text.split("zł")[0])


def _locality(location):
    """City = the broadest (last) breadcrumb part of 'street, district, city',
    e.g. 'Tarnogórska, Szobiszowice, Gliwice' -> 'Gliwice' (taking the first
    segment stored street names like 'Tarnogórska' as fake towns)."""
    if not location:
        return None
    parts = [p.strip() for p in location.replace("śląskie", "").split(",") if p.strip()]
    if not parts:
        return None
    city = parts[-1]
    return "Gliwice" if city.startswith("Gliwice") else (city or None)


def _district(location):
    """The narrower part(s) before the city, e.g. 'Tarnogórska, Szobiszowice'."""
    if not location:
        return None
    parts = [p.strip() for p in location.replace("śląskie", "").split(",") if p.strip()]
    inner = parts[:-1]
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
        out.append({
            "source": "morizon",
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


def scrape(max_pages: int = 50, delay: float = 0.7, session=None, log=print,
           types=("house", "flat")):
    session = session or requests.Session()
    out = []
    for typ, bases in SEARCH.items():
        if typ not in types:
            continue
        seen = set()
        for base in bases:
            tag = base.rstrip("/").split("/")[-1]
            page = 1
            while page <= max_pages:
                url = base if page == 1 else f"{base}?page={page}"
                try:
                    r = session.get(url, headers=HEADERS, timeout=30)
                    if r.status_code == 404:
                        break
                    r.raise_for_status()
                    batch = [c for c in parse_cards(r.text, typ) if c["url"] not in seen]
                except Exception as exc:  # keep what we have, move on
                    log(f"  morizon {typ}/{tag} page {page} error: {exc}")
                    break
                for c in batch:
                    seen.add(c["url"])
                out.extend(batch)
                log(f"  morizon {typ}/{tag} page {page}: +{len(batch)}")
                if not batch:
                    break
                page += 1
                time.sleep(delay)
    return out
