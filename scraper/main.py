"""Entry point: scrape every source, de-duplicate, track history, write data.

Run from the repo root:

    python -m scraper.main

Environment overrides (optional):
    RENTGEN_MAX_PAGES   max pages per source/type (default 50)
    RENTGEN_DELAY       seconds between requests   (default 0.7)
    RENTGEN_TYPES       which to scrape, e.g. "house" (default "house,flat")
    RENTGEN_PHOTOS      "0" to skip photo hashing (disables dedupe-by-photo and
                        relist/price history)
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import sys

from . import cache as phcache
from . import gratka, history, morizon, net, nieruchomosci_online, olx, otodom, photomatch
from .normalize import dedupe, link_same_size

DATA_DIR = pathlib.Path(__file__).resolve().parents[1] / "site" / "data"
CACHE_PATH = pathlib.Path(__file__).resolve().parents[1] / "cache" / "phash_cache.json"

SOURCES = (
    ("otodom", otodom),
    ("olx", olx),
    ("gratka", gratka),
    ("morizon", morizon),
    ("nieruchomosci-online", nieruchomosci_online),
)


def run() -> int:
    max_pages = int(os.environ.get("RENTGEN_MAX_PAGES", "50"))
    delay = float(os.environ.get("RENTGEN_DELAY", "0.7"))
    types = tuple(t.strip() for t in os.environ.get("RENTGEN_TYPES", "house,flat").split(",") if t.strip())

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

    # Fingerprint every listing by its gallery photos. Powers both photo-based
    # de-duplication and the relist/price history below. A committed cache
    # (cache/phash_cache.json) lets repeat runs reuse hashes by listing URL and
    # skip the slow detail-page + image fetches.
    if os.environ.get("RENTGEN_PHOTOS", "1") != "0":
        print(f"Photo-hashing {len(raw)} listings (dedupe + history) ...")
        pc = phcache.load(CACHE_PATH)
        photomatch.attach_hashes(raw, session=http, cache=pc, today=today)
        pruned = phcache.prune(pc, today)
        phcache.save(CACHE_PATH, pc)
        print(f"  phash cache: {len(pc.get('entries', {}))} urls "
              f"({pruned} pruned as stale)")

    listings = dedupe(raw)

    # Relist + price history: match today's properties to what we've seen before.
    hist_path = DATA_DIR / "history.json"
    records = history.load(hist_path)
    history.update(listings, records, today)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    history.save(hist_path, records)
    link_same_size(listings)   # flag same-area duplicates/relists visible right now
    relisted = sum(1 for l in listings if l.get("relisted"))

    # newest first when a timestamp is available
    listings.sort(key=lambda l: (l.get("created") or ""), reverse=True)
    for p in listings:                 # drop bulky hashes before publishing
        p.pop("phashes", None)

    (DATA_DIR / "listings.json").write_text(
        json.dumps(listings, ensure_ascii=False, indent=1), encoding="utf-8")

    by_source = {}
    for x in raw:
        by_source[x["source"]] = by_source.get(x["source"], 0) + 1

    meta = {
        "updated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "count": len(listings),
        "raw": len(raw),
        "by_source": by_source,
        "by_type": {
            "house": sum(1 for x in listings if x["type"] == "house"),
            "flat": sum(1 for x in listings if x["type"] == "flat"),
        },
        "relisted": relisted,
        "errors": errors,
    }
    (DATA_DIR / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")

    summary = ", ".join(f"{k} {v}" for k, v in by_source.items())
    print(f"Done: {len(listings)} unique properties from {len(raw)} raw ({summary}); "
          f"{relisted} flagged as relisted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
