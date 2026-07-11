"""nieruchomosci-online.pl scraper for Gliwice + nearby towns.

Each town is a sub-domain (e.g. ``pyskowice.nieruchomosci-online.pl``) whose
result pages embed a schema.org ``CollectionPage`` JSON-LD block. Rental
listings are skipped; archived ("OutOfStock"/"SoldOut") listings are returned
with ``archived: True`` — main.py keeps them out of the dashboard but feeds
them to the history store as evidence the ad ended (likely sold).
"""
from __future__ import annotations

import json
import os
import re
import time

import requests

from .normalize import to_float, to_int

# nieruchomosci-online uses one sub-domain per town; a missing sub-domain is
# skipped gracefully (see scrape()), so this list is deliberately generous.
# Śląskie: the cities with powiat rights plus major towns. The long tail of
# villages is still covered by the other portals' region-wide searches.
REGION = os.environ.get("RENTGEN_REGION", "slaskie")
# sub-domain slug -> proper display name (the slug loses Polish diacritics, so
# `slug.title()` would leak fake localities like "Dabrowa-Gornicza" into the
# data and break locality-keyed dedupe/geocoding for offers without an address)
SLASKIE_TOWNS = {
    "katowice": "Katowice", "gliwice": "Gliwice", "zabrze": "Zabrze",
    "bytom": "Bytom", "sosnowiec": "Sosnowiec", "czestochowa": "Częstochowa",
    "tychy": "Tychy", "rybnik": "Rybnik", "dabrowa-gornicza": "Dąbrowa Górnicza",
    "bielsko-biala": "Bielsko-Biała", "ruda-slaska": "Ruda Śląska",
    "jastrzebie-zdroj": "Jastrzębie-Zdrój", "jaworzno": "Jaworzno",
    "chorzow": "Chorzów", "myslowice": "Mysłowice",
    "siemianowice-slaskie": "Siemianowice Śląskie",
    "tarnowskie-gory": "Tarnowskie Góry", "bedzin": "Będzin",
    "piekary-slaskie": "Piekary Śląskie", "raciborz": "Racibórz",
    "swietochlowice": "Świętochłowice", "zory": "Żory",
    "wodzislaw-slaski": "Wodzisław Śląski", "mikolow": "Mikołów",
    "knurow": "Knurów", "czeladz": "Czeladź", "lubliniec": "Lubliniec",
    "pszczyna": "Pszczyna", "czechowice-dziedzice": "Czechowice-Dziedzice",
    "zawiercie": "Zawiercie", "cieszyn": "Cieszyn", "myszkow": "Myszków",
    "klobuck": "Kłobuck", "bierun": "Bieruń", "laziska-gorne": "Łaziska Górne",
    "rydultowy": "Rydułtowy", "orzesze": "Orzesze", "pyskowice": "Pyskowice",
    "ornontowice": "Ornontowice", "zbroslawice": "Zbrosławice",
    "pilchowice": "Pilchowice", "gieraltowice": "Gierałtowice",
    "sosnicowice": "Sośnicowice", "toszek": "Toszek", "rudziniec": "Rudziniec",
    "wielowies": "Wielowieś", "rzeczyce": "Rzeczyce",
}
TOWNS = list(SLASKIE_TOWNS) if REGION == "slaskie" else [REGION]


def town_name(slug):
    return SLASKIE_TOWNS.get(slug) or (slug.replace("-", " ").title() if slug else None)
PATHS = {"house": "domy", "flat": "mieszkania"}
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8",
}
_LD = re.compile(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.S)
ARCHIVED = {"OutOfStock", "SoldOut", "Discontinued"}


def extract_offers(html: str):
    for m in _LD.finditer(html):
        try:
            block = json.loads(m.group(1).strip())
        except ValueError:
            continue
        if isinstance(block, dict) and block.get("@type") == "CollectionPage":
            agg = (block.get("mainEntity") or {}).get("offers") or []
            if agg and isinstance(agg, list):
                return agg[0].get("offers", []) or []
    return []


def parse_offers(offers, typ: str, town: str = ""):
    out = []
    for o in offers:
        url = o.get("url") or ""
        if "na-wynajem" in url:
            continue
        archived = (o.get("availability") or "").rsplit("/", 1)[-1] in ARCHIVED
        item = o.get("itemOffered") or {}
        addr = item.get("address") or {}
        floor = item.get("floorSize") or {}
        spec = o.get("priceSpecification") or {}
        out.append({
            "source": "nieruchomosci-online",
            "source_id": (re.search(r"/(\d+)\.html", url) or [None, None])[1] or url,
            "url": url,
            "title": o.get("name") or item.get("description"),
            "type": typ,
            "price": to_int(o.get("price")),
            "area": to_float(floor.get("value")),
            "price_per_m2": to_int(spec.get("price")),
            "rooms": to_int(item.get("numberOfRooms")),
            "plot_area": None,
            "floor": None,
            "locality": addr.get("addressLocality") or town_name(town),
            "district": None,
            "street": addr.get("streetAddress") or None,
            "is_private": None,
            "agency": None,
            "image": o.get("image"),
            "created": None,
            "also_on": [],
            # kept (not skipped) so history can record "the portal archived this
            # ad" — main.py routes archived listings to history, not the dashboard
            "archived": archived,
        })
    return out


def scrape(max_pages: int = 50, delay: float = 0.7, session=None, log=print,
           types=("house", "flat")):
    session = session or requests.Session()
    out = []
    for typ, path in PATHS.items():
        if typ not in types:
            continue
        seen = set()
        for town in TOWNS:
            base = f"https://{town}.nieruchomosci-online.pl/{path}/"
            page = 1
            dup_pages = 0
            while page <= max_pages:
                url = base if page == 1 else f"{base}?p={page}"
                try:
                    r = session.get(url, headers=HEADERS, timeout=30)
                    r.raise_for_status()
                    batch = parse_offers(extract_offers(r.text), typ, town)
                except Exception as exc:  # missing sub-domain etc. -> skip town
                    log(f"  nieruchomosci-online {typ}/{town} page {page} error: {exc}")
                    break
                fresh = [b for b in batch if b["url"] not in seen]
                for b in fresh:
                    seen.add(b["url"])
                out.extend(fresh)
                if fresh:
                    log(f"  nieruchomosci-online {typ}/{town} page {page}: +{len(fresh)}")
                if not batch:
                    break              # empty result page = past the end
                if not fresh:
                    # towns cross-list each other's offers, so a page can be all
                    # already-seen URLs while later pages still hold new ones —
                    # only stop after two such pages in a row (also bounds the
                    # portals that echo the last page forever when paged past it)
                    dup_pages += 1
                    if dup_pages >= 2:
                        break
                else:
                    dup_pages = 0
                page += 1
                time.sleep(delay)
    return out
