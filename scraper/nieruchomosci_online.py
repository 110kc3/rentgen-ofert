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
SLASKIE_TOWNS = [
    "katowice", "gliwice", "zabrze", "bytom", "sosnowiec", "czestochowa",
    "tychy", "rybnik", "dabrowa-gornicza", "bielsko-biala", "ruda-slaska",
    "jastrzebie-zdroj", "jaworzno", "chorzow", "myslowice",
    "siemianowice-slaskie", "tarnowskie-gory", "bedzin", "piekary-slaskie",
    "raciborz", "swietochlowice", "zory", "wodzislaw-slaski", "mikolow",
    "knurow", "czeladz", "lubliniec", "pszczyna", "czechowice-dziedzice",
    "zawiercie", "cieszyn", "myszkow", "klobuck", "bierun", "laziska-gorne",
    "rydultowy", "orzesze", "pyskowice", "ornontowice", "zbroslawice",
    "pilchowice", "gieraltowice", "sosnicowice", "toszek", "rudziniec",
    "wielowies", "rzeczyce",
]
TOWNS = SLASKIE_TOWNS if REGION == "slaskie" else [REGION]
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
            "locality": addr.get("addressLocality") or (town.title() if town else None),
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
                if not fresh:
                    break
                page += 1
                time.sleep(delay)
    return out
