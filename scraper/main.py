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
    #   3. history.update — matches today's listings, builds snapshots
    #   4. RCN match — needs snapshots + `delisted` dates; cards re-enriched after
    hist_path = DATA_DIR / "history.json"
    records = history.compact(history.load(hist_path))
    active_urls = {o.get("url") for l in listings for o in l.get("offers", [])}
    active_urls |= {l.get("url") for l in listings}
    active_urls.discard(None)

    n_arch = history.observe_archived(archived_raw, records, today)
    if archived_raw:
        print(f"  archived ads ingested into history: {n_arch}/{len(archived_raw)}")
    if verify_max > 0:
        delist.sweep(records, today, http, active_urls=active_urls,
                     max_checks=verify_max)

    history.update(listings, records, today)

    # Real sale prices from notarial deeds (RCN) matched onto our records.
    # Runs after update so brand-new records already carry a snapshot
    # (locality/street/rooms) to match on; the affected cards are re-enriched.
    if rcn_mode != "0":
        region = os.environ.get("RENTGEN_REGION", "slaskie")
        teryt = TERYT.get(region)
        if teryt:
            snap = rcn.refresh(RCN_CACHE, http, teryt_prefix=teryt, today=today,
                               force=(rcn_mode == "force"))
            if snap:
                rcn.match(records, snap)
        else:
            print(f"RCN: no TERYT mapping for region '{region}', skipping")
    history.reenrich(listings)   # always: also drops the transient _rec links

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

    # Delisted/sold properties -> their own feed for the "Archiwum" view.
    archive = history.build_archive(records)
    (DATA_DIR / "archive.json").write_text(
        json.dumps(archive, ensure_ascii=False, indent=1), encoding="utf-8")

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
        "archive": len(archive),
        "sold_confirmed": sum(1 for a in archive if a.get("sold")),
        "errors": errors,
    }
    (DATA_DIR / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")

    summary = ", ".join(f"{k} {v}" for k, v in by_source.items())
    print(f"Done: {len(listings)} unique properties from {len(raw)} raw ({summary}); "
          f"{relisted} flagged as relisted; {len(archive)} in archive.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
