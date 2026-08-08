"""Entry point: scrape every source, de-duplicate, track history, write data.

Run from the repo root:

    python -m scraper.main

Environment overrides (optional):
    RENTGEN_MAX_PAGES   max pages per source/type (default 200; CI deliberately
                        does NOT set it — it was pinned to 50 there, which
                        overrode this default on every scheduled run)
    RENTGEN_DELAY       seconds between requests   (default 0.7)
    RENTGEN_TYPES       which to scrape, e.g. "house" (default "house,flat")
    RENTGEN_PHOTOS      "0" to skip photo hashing (disables dedupe-by-photo and
                        relist/price history)
    RENTGEN_VERIFY_MAX  max stale listings URL-verified per run (default 300;
                        "0" disables the delist sweep)
    RENTGEN_RCN         "0" = skip RCN, "force" = re-pull now; default refreshes
                        the cached snapshot when it's older than 7 days
    RENTGEN_GEO         "0" = skip geocoding listings for the map view
    RENTGEN_GEO_MAX     max new UUG geocoder lookups per run (default 500)
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import sys

from . import cache as phcache
from . import coverage, delist, geo, gratka, history, marketstats, morizon, net, nieruchomosci_online, olx, otodom, overrides, payload, photomatch, rcn, rcnstats
from .normalize import dedupe, link_same_size

# Region = the unit of everything (data dir, caches, RCN snapshot). Output goes
# to site/data/<region>/ and per-region cache files so more voivodeships can be
# added side by side; the geocode cache is shared (a town looked up once serves
# every region). All of it lives on the orphan `data` branch, NOT in main's
# history (see TODO.md "storage switch").
ROOT = pathlib.Path(__file__).resolve().parents[1]
REGION = os.environ.get("RENTGEN_REGION", "slaskie")
DATA_DIR = ROOT / "site" / "data" / REGION
CACHE_DIR = ROOT / "cache"
CACHE_PATH = CACHE_DIR / f"phash_{REGION}.json"
RCN_CACHE = CACHE_DIR / f"rcn_{REGION}.json.gz"
GEO_CACHE = CACHE_DIR / "geo_cache.json"
NOL_TOWNS = CACHE_DIR / "nol_towns.json"   # per-region town lists for n-online

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
    # 200, not the old 50: with 50 EVERY paginated portal stopped on our cap
    # inside śląskie alone (gratka's domy search alone runs to page 72 and only
    # then 404s, so ~700 houses were being dropped silently). The scrapers all
    # terminate on the portal's own end, so a generous cap costs nothing where
    # it isn't needed and `coverage` reports it when it still binds.
    max_pages = int(os.environ.get("RENTGEN_MAX_PAGES", "200"))
    delay = float(os.environ.get("RENTGEN_DELAY", "0.7"))
    types = tuple(t.strip() for t in os.environ.get("RENTGEN_TYPES", "house,flat").split(",") if t.strip())
    verify_max = int(os.environ.get("RENTGEN_VERIFY_MAX", "300"))
    rcn_mode = os.environ.get("RENTGEN_RCN", "1")

    today = dt.date.today().isoformat()
    raw = []
    errors = []
    http = net.session()
    cov_rows = []
    for name, mod in SOURCES:
        kwargs = dict(max_pages=max_pages, delay=delay, types=types, session=http)
        if mod is olx:
            # OLX caps its own pagination; a capped search is re-run per town.
            # Towns come from the same resolver n-online uses, but OLX runs
            # BEFORE the others have filled `raw`, so this leans on the cached
            # list from previous runs (empty on a region's very first run —
            # subdivision then starts one run later, which is harmless).
            kwargs["towns"] = nieruchomosci_online.resolve_towns(
                REGION, raw, cache_path=NOL_TOWNS)
        if mod is nieruchomosci_online:
            # This portal has no region-wide search — it needs a town list, and
            # the portal publishes no index to build one from. Derive it from the
            # localities the other four just returned (they run first in SOURCES
            # precisely for this) so a brand-new region works on its first run.
            kwargs["towns"] = nieruchomosci_online.resolve_towns(
                REGION, raw, cache_path=NOL_TOWNS)
            print(f"  n-online towns for {REGION}: {len(kwargs['towns'])}")
        try:
            print(f"Scraping {name} ...")
            raw.extend(mod.scrape(**kwargs))
        except Exception as exc:  # one portal failing must not lose the others
            errors.append(f"{name}: {exc}")
            print(f"  !! {name} failed: {exc}", file=sys.stderr)
        cov_rows.extend(getattr(mod.scrape, "last_coverage", None) or [])

    # Truncation is silent by nature — a capped search returns a plausible pile
    # of listings and no hint that more exist. Say so, loudly, every run.
    for line in coverage.warnings(cov_rows):
        print(line, file=sys.stderr)
        errors.append(line.strip().lstrip("! "))

    # Coverage as a number, so two runs are comparable without diffing stop
    # reasons. `pct` is a floor: each scraper filters while parsing (otodom
    # drops INVESTMENT bundles, olx drops Otodom-syndicated ads), so even a
    # complete search lands below 100%.
    cov_summary = coverage.summarise(cov_rows)
    for name, s in cov_summary["by_source"].items():
        total = s.get("portal_total")
        against = (f" of {'≥' if s.get('total_is_min') else ''}{total}"
                   f" the portals state ({s['pct']}%)" if total else "")
        print(f"  coverage {name}: {s['listings']} listings from {s['searches']} "
              f"search(es), {s['pages']} pages{against}"
              + (f", {s['truncated']} truncated" if s["truncated"] else ""))

    if not raw:
        print("No listings collected - aborting (keeping previous data).", file=sys.stderr)
        return 1

    # Fingerprint every listing by its gallery photos. Powers photo-based
    # de-duplication, the relist/price history and the photo archive. A
    # committed cache (cache/phash_cache.json) lets repeat runs reuse hashes
    # (and gallery URLs) by listing URL and skip the slow detail fetches.
    # Archived ads are hashed too (BEFORE the split below) so observe_archived
    # can still photo-match them when their URL was never seen live.
    if os.environ.get("RENTGEN_PHOTOS", "1") != "0":
        print(f"Photo-hashing {len(raw)} listings (dedupe + history) ...")
        pc = phcache.load(CACHE_PATH)
        budget_min = float(os.environ.get("RENTGEN_PHOTO_BUDGET_MIN", "90"))
        photomatch.attach_hashes(raw, session=http, cache=pc, today=today,
                                 budget_s=budget_min * 60 if budget_min > 0 else None)
        pruned = phcache.prune(pc, today)
        phcache.save(CACHE_PATH, pc)
        print(f"  phash cache: {len(pc.get('entries', {}))} urls "
              f"({pruned} pruned as stale)")

    # Portal-archived ads (n-online flags them) are history evidence, not offers.
    archived_raw = [x for x in raw if x.get("archived")]
    raw = [x for x in raw if not x.get("archived")]

    listings = dedupe(raw)

    # Lifecycle bookkeeping, in dependency order:
    #   1. ingest portal-archived ads (direct "this ad ended" evidence)
    #   2. delist sweep — URL-verify records that vanished from scrapes
    #   3. history.update — matches today's listings, builds snapshots
    #   4. RCN match — needs snapshots + `delisted` dates; cards re-enriched after
    hist_path = DATA_DIR / "history.json.gz"
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
    overrides.apply(records, overrides.load())   # hand-pinned addresses win

    # Real sale prices from notarial deeds (RCN) matched onto our records.
    # Runs after update so brand-new records already carry a snapshot
    # (locality/street/rooms) to match on; the affected cards are re-enriched.
    rcn_stats = None
    snap = None
    if rcn_mode != "0":
        teryt = TERYT.get(REGION)
        if teryt:
            snap = rcn.refresh(RCN_CACHE, http, teryt_prefix=teryt, today=today,
                               force=(rcn_mode == "force"))
            if snap:
                rcn.match(records, snap)
                # town/size-bucket deed benchmarks + ask-vs-sold gap for the
                # dashboard's "cena vs transakcje RCN" comparison
                rcn_stats = rcnstats.build(snap, records, today)
        else:
            print(f"RCN: no TERYT mapping for region '{REGION}', skipping")
    history.reenrich(listings)   # always: also drops the transient _rec links

    # Coordinates for the map view (UUG geocoder, cached; towns first).
    geocoded = 0
    if os.environ.get("RENTGEN_GEO", "1") != "0":
        gc = geo.load(GEO_CACHE)
        _, geocoded = geo.attach(
            listings, gc, session=http, today=today,
            max_new=int(os.environ.get("RENTGEN_GEO_MAX", "500")))
        geo.save(GEO_CACHE, gc)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    history.save(hist_path, records)
    link_same_size(listings)   # flag same-area duplicates/relists visible right now
    relisted = sum(1 for l in listings if l.get("relisted"))

    # newest first when a timestamp is available
    listings.sort(key=lambda l: (l.get("created") or ""), reverse=True)
    for p in listings:                 # drop bulky hashes before publishing
        p.pop("phashes", None)

    # dashboard payload: slim index + lazy detail shards (replaces the old
    # monolithic listings.json — see scraper/payload.py)
    payload.build(listings, DATA_DIR)
    (DATA_DIR / "listings.json").unlink(missing_ok=True)   # pre-split leftover

    if rcn_stats:
        (DATA_DIR / "rcnstats.json").write_text(
            json.dumps(rcn_stats, ensure_ascii=False, indent=0), encoding="utf-8")

    # Market time series for the "Statystyki" page (works without RCN too —
    # the deed lines just stay empty then).
    mstats = marketstats.build(records, snap, today)
    (DATA_DIR / "stats.json").write_text(
        json.dumps(mstats, ensure_ascii=False, indent=0), encoding="utf-8")

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
        "geocoded": geocoded,
        "archive": len(archive),
        "rcn": getattr(rcn.match, "last_funnel", None),
        "rcn_stats": {"towns": len(rcn_stats["towns"]),
                      "gap_pairs": (rcn_stats["gap"].get("all") or {}).get("n", 0)}
                     if rcn_stats else None,
        "sold_confirmed": sum(1 for a in archive if a.get("sold")),
        "coverage": cov_summary,
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
