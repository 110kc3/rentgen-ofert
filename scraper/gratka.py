"""gratka.pl scraper for Gliwice + powiat gliwicki sale listings.

gratka hydrates its Nuxt state client-side (``window.__NUXT__`` is empty) but
renders result cards server-side with stable ``data-cy`` hooks, parsed here with
BeautifulSoup. Gliwice city and the surrounding powiat are separate search URLs.
"""
from __future__ import annotations

import re
import time

import requests
from bs4 import BeautifulSoup

from .normalize import to_float, to_int

BASE = "https://gratka.pl"
SEARCH = {
    "house": [
        "https://gratka.pl/nieruchomosci/domy/gliwice",
        "https://gratka.pl/nieruchomosci/domy/slaskie/powiat-gliwicki",
    ],
    "flat": [
        "https://gratka.pl/nieruchomosci/mieszkania/gliwice",
        "https://gratka.pl/nieruchomosci/mieszkania/slaskie/powiat-gliwicki",
    ],
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
    """The town/city, e.g. 'Pyskowice'; Gliwice districts collapse to 'Gliwice'."""
    if not location:
        return None
    city = location.split(",")[0].strip()
    return "Gliwice" if city.startswith("Gliwice") else (city or None)


def _district(location):
    if not location:
        return None
    toks = location.replace("śląskie", "").strip(" ,")
    return None if toks in ("", "Gliwice") else toks


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
                        break  # gratka 404s once you page past the last results page
                    r.raise_for_status()
                    batch = [c for c in parse_cards(r.text, typ) if c["url"] not in seen]
                except Exception as exc:  # keep what we have, move on
                    log(f"  gratka {typ}/{tag} page {page} error: {exc}")
                    break
                for c in batch:
                    seen.add(c["url"])
                out.extend(batch)
                log(f"  gratka {typ}/{tag} page {page}: +{len(batch)}")
                if not batch:
                    break
                page += 1
                time.sleep(delay)
    return out
