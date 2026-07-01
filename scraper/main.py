"""Entry point: scrape every source, de-duplicate, track history, write data.

Run from the repo root:

    python -m scraper.main

Environment overrides (optional):
    RENTGEN_MAX_PAGES   max pages per source/type (default 50)
    RENTGEN_DELAY       seconds between requests   (default 0.7)
    RENTGEN_TYPES       which to scrape, e.g. "house" (default "house,flat")
    RENTGEN_PHOTOS      "0" to skip photo hashing (disables dedupe-by-photo and
                        relist/price history)
    RENTGEN_VERIFY_MAX  max stale listings URL-verified per run (default 300;
                        "0" disables the delist sweep)
    RENTGEN_RCN         "0" = skip RCN, "force" = re-pull now; default refreshes
                        the cached snapshot when it's older than 7 days
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import sys

from . import cache as phcache
from . import delist, gratka, history, morizon, net, nieruchomosci_online, olx, otodom, photomatch, rcn
from .normalize import dedupe, link_same_size

DATA_DIR = pathlib.Path(__file__).resolve().parents[1] / "site" / "data"
CACHE_DIR = pathlib.Path(__file__).resolve().parents[1] / "cache"
CACHE_PATH = CACHE_DIR / "phash_cache.json"
RCN_CACHE = CACHE_DIR / "rcn_snapshot.json.gz"

SOURCES = (
    ("otodom", otodom),
    ("olx", olx),
    ("gratka", gratka),
    ("morizon", morizon),
    ("nieruchomosci-online", nieruchomosci_online),
)

# voivodeship slug -> TERYT prefix (for the RCN transaction pull)
TERYT = {
    "dolnoslaskie": "02", "kujawsko-pomorskie": "04", "lubelskie": "06",
    "lubuskie": "08", "lodzkie": "10", "malopolskie": "12", "mazowieckie": "14",
    "opolskie": "16", "podkarpackie": "18", "podlaskie": "20", "pomorskie": "22",
    "slaskie": "24", "swietokrzyskie": "26", "warminsko-mazurskie": "28",
    "wielkopolskie": "30", "zachodniopomorskie": "32",
}


def run() -> int:
    max_pages = int(os.environ.get("RENTGEN_MAX_PAGES", "50"))
    delay = float(os.environ.get("RENTGEN_DELAY", "0.7"))
    types = tuple(t.strip() for t in os.environ.get("RENTGEN_TYPES", "house,flat").split(",") if t.strip())
    verify_max = int(os.environ.get("RENTGEN_VERIFY_MAX", "300"))
    rcn_mode = os.environ.get("RENTGEN_RCN", "1")

    today = dt.date.today().isoformat()
    raw = []
    errors = []
    http = net.session()
    for name, mod in SOURCES:
        try:
            print(f"Scraping {name} ...")
            raw.extend(mod.scrape(max_pages=max_pages, delay=delay, types=types, session=http))
        except Exception as exc:  # one portal failing must not lose the others
            errors.append(f"{name}: {exc}")
            print(f"  !! {name} failed: {exc}", file=sys.stderr)

    if not raw:
        print("No listings collected - aborting (keeping previous data).", file=sys.stderr)
        return 1

    # Portal-archived ads (n-online flags them) are history evidence, not offers.
    archived_raw = [x for x in raw if x.get("archived")]
    raw = [x for x in raw if not x.get("archived")]

    # Fingerprint every listing by its gallery photos. Powers photo-based
    # de-duplication, the relist/price history and the photo archive. A
    # committed cache (cache/phash_cache.json) lets repeat runs reuse hashes
    # (and gallery URLs) by listing URL and skip the slow detail fetches.
    if os.environ.get("RENTGEN_PHOTOS", "1") != "0":
        print(f"Photo-hashing {len(raw)} listings (dedupe + history) ...")
        pc = phcache.load(CACHE_PATH)
        photomatch.attach_hashes(raw, session=http, cache=pc, today=today)
        pruned = phcache.prune(pc, today)
        phcache.save(CACHE_PATH, pc)
        print(f"  phash cache: {len(pc.get('entries', {}))} urls "
              f"({pruned} pruned as stale)")

    listings = dedupe(raw)

    # Lifecycle bookkeeping, in dependency order:
    #   1. ingest portal-archived ads (direct "this ad ended" evidence)
    #   2. delist sweep — URL-verify records that vanished from scrapes
    #   3. RCN match — needs `delisted` dates to time-window "sold" deeds
    #   4. history.update — enriches today's listings from the records
    #      (timeline / sales / photo archive), so it runs last.
    hist_path = DATA_DIR / "history.json"
    records = history.compact(history.load(hist_path))
    active_urls = {o.get("url") for l in listings for o in l.get("offers", [])}