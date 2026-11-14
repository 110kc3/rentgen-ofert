"""Entry point: scrape every source, de-duplicate, track history, write data.

Run from the repo root:

    python -m scraper.main

Environment overrides (optional):
    RENTGEN_MAX_PAGES   max pages per source/type (default 200; CI deliberately
                        does NOT set it — it was pinned to 50 there, which
                        overrode this default on every scheduled run)
    RENTGEN_DELAY       seconds between requests   (default 0.7)
    RENTGEN_TYPES       which to scrape, e.g. "house" (default "house,flat")
    RENTGEN_BANDS       "0" to disable price-band subdivision (see scraper/bands.py);
                        the escape hatch if a portal starts rejecting the filters
    RENTGEN_OTODOM_BANDS
                        "1" to opt into Otodom bands *after* its full unbanded
                        baseline (default 0; repeated 405s made them regress)
    RENTGEN_PHOTOS      "0" to skip photo hashing (disables dedupe-by-photo and
                        relist/price history, and explicitly enables the loose
                        size/price fallback)
    RENTGEN_PHOTO_BUDGET_MIN
                        max minutes spent fetching uncached photos (default 90;
                        "0" = unlimited). Critical current collisions hash one
                        card cover first; full galleries fill the age-persisted
                        history-only backlog afterwards
    RENTGEN_DELIST_BUDGET_MIN
                        max minutes the delist sweep may spend (default 10,
                        "0" = unlimited); unasked records retry next run
    RENTGEN_VERIFY_MAX  max stale listings URL-verified per run (default 300;
                        "0" disables the delist sweep)
    RENTGEN_RCN         "0" = skip RCN, "force" = re-pull now; default refreshes
                        the cached snapshot when it's older than 7 days
    RENTGEN_GEO         "0" = skip geocoding listings for the map view
    RENTGEN_GEO_MAX     max new UUG geocoder lookups per run (default 500)
    RENTGEN_NOL_ARCHIVE auto = start weekly archive cycle or resume pending work;
                        force = start/resume now; skip = current listings only
    RENTGEN_NOL_ARCHIVE_DAYS
                        days after completed archive cycle (default 7)
    RENTGEN_NOL_ARCHIVE_BUDGET_MIN
                        maintenance minutes after current stock (default 15)
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import sys
import time

from . import cache as phcache
from . import (
    coverage, delist, geo, gratka, history, marketstats, morizon, net,
    nieruchomosci_online, olx, otodom, overrides, payload, photomatch, rcn,
    rcnstats, regions,
)
from .normalize import dedupe, link_same_size, link_twins, require_unique_urls

ROOT = pathlib.Path(__file__).resolve().parents[1]
REGION = os.environ.get("RENTGEN_REGION", "slaskie")
REGION_CONFIG = regions.get_region(REGION)
DATA_DIR = ROOT / "site" / "data" / REGION
CACHE_DIR = ROOT / "cache"
CACHE_PATH = CACHE_DIR / f"phash_{REGION}.json.gz"
RCN_CACHE = CACHE_DIR / f"rcn_{REGION}.json.gz"
GEO_CACHE = CACHE_DIR / "geo_cache.json"
NOL_TOWNS = CACHE_DIR / "nol_towns.json"
NOL_ARCHIVE_STATE = CACHE_DIR / f"nol_archive_{REGION}.json"

SOURCES = (
    ("otodom", otodom),
    ("olx", olx),
    ("gratka", gratka),
    ("morizon", morizon),
    ("nieruchomosci-online", nieruchomosci_online),
)

def run() -> int:
    run_started = time.monotonic()
    phase_seconds = {}
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
    banded = os.environ.get("RENTGEN_BANDS", "1") != "0"
    otodom_banded = (banded
                      and os.environ.get("RENTGEN_OTODOM_BANDS", "0") == "1")
    nol_archive_state = nieruchomosci_online.load_archive_state(
        NOL_ARCHIVE_STATE, DATA_DIR / "meta.json")
    nol_archive_mode = os.environ.get("RENTGEN_NOL_ARCHIVE", "auto")
    pending_archive_state = None
    nol_archive_days = int(os.environ.get("RENTGEN_NOL_ARCHIVE_DAYS", "7"))
    nol_harvest_archive = nieruchomosci_online.archive_due(
        nol_archive_state, today, nol_archive_mode, nol_archive_days)
    for name, mod in SOURCES:
        source_started = time.monotonic()
        mod.scrape.last_coverage = []
        kwargs = dict(max_pages=max_pages, delay=delay, types=types, session=http)
        if mod is not nieruchomosci_online:
            kwargs["banded"] = otodom_banded if mod is otodom else banded
        if mod is olx:
            kwargs["towns"] = nieruchomosci_online.resolve_towns(
                REGION, raw, cache_path=NOL_TOWNS)
        if mod is nieruchomosci_online:
            kwargs["towns"] = nieruchomosci_online.resolve_towns(
                REGION, raw, cache_path=NOL_TOWNS)
            kwargs["region"] = REGION
            print(f"  n-online towns for {REGION}: {len(kwargs['towns'])}")
            kwargs.update(
                harvest_archive=nol_harvest_archive,
                archive_state=nol_archive_state,
                today=today,
                archive_budget_s=float(os.environ.get("RENTGEN_NOL_ARCHIVE_BUDGET_MIN", "15")) * 60,
                archive_session=net.probe_session(),
            )
            archive_action = ("bounded archive refresh/resume" if nol_harvest_archive
                              else "current-only; archive cache "
                              + (nol_archive_state.get("refreshed") or
                                 "unavailable"))
            print(f"  n-online mode: {archive_action}")
        try:
            print(f"Scraping {name} ...")
            raw.extend(mod.scrape(**kwargs))
            if mod is nieruchomosci_online and mod.scrape.last_archive_state:
                pending_archive_state = mod.scrape.last_archive_state
        except Exception as exc:
            errors.append(f"{name}: {exc}")
            print(f"  !! {name} failed: {exc}", file=sys.stderr)
            error, http_status = coverage.error_details(exc)
            mod.scrape.last_coverage = [coverage.row(
                name, typ, REGION, 0, 0, coverage.ERROR,
                role=coverage.PARENT, error=error,
                http_status=http_status) for typ in types]
        phase_seconds[f"scrape_{name}"] = round(
            time.monotonic() - source_started, 1)
        cov_rows.extend(getattr(mod.scrape, "last_coverage", None) or [])

    for line in coverage.warnings(cov_rows):
        print(line, file=sys.stderr)
        errors.append(line.strip().lstrip("! "))

    cov_summary = coverage.summarise(
        cov_rows, listings=raw, expected_sources=[name for name, _ in SOURCES],
        expected_types=types)
    for name, s in cov_summary["by_source"].items():
        total = s.get("portal_total")
        against = (f" of {'≥' if s.get('total_is_min') else ''}{total}"
                   f" the portals state ({s['pct']}%)" if total else "")
        kept = (f", kept {s['kept_unique']}"
                if s["served_unique"] != s["kept_unique"] else "")
        archive = f", archived {s['archived']}" if s["archived"] else ""
        harvest = s.get("archive_harvest") or {}
        archive_cache = (f", archive {harvest.get('mode')} "
                         f"{harvest.get('records', 0)} as of "
                         f"{harvest.get('refreshed')}"
                         if harvest.get("refreshed") else "")
        print(f"  coverage {name} [{s['status']}]: {s['served_unique']} unique "
              f"served from {s['searches']} search(es), {s['pages']} pages"
              f"{against}{kept}{archive}{archive_cache}"
              + (f", {s['truncated']} issue(s)" if s["truncated"] else ""))

    if not raw:
        print("No listings collected - aborting (keeping previous data).", file=sys.stderr)
        return 1

    require_unique_urls(raw, "raw scrape")

    photo_started = time.monotonic()
    linked = link_twins(raw)
    if linked:
        print(f"  gratka<->morizon twins linked off the search page: {linked}")

    photos_enabled = os.environ.get("RENTGEN_PHOTOS", "1") != "0"
    photo_stats = {
        "schema": 3,
        "enabled": photos_enabled,
        "listings": len(raw),
        "heuristic_fallback_enabled": not photos_enabled,
    }
    if photos_enabled:
        print(f"Photo-hashing {len(raw)} listings (dedupe + history) ...")
        pc = phcache.load(CACHE_PATH)
        photo_queue, critical_urls = photomatch.prioritize(
            raw, cache=pc, today=today)
        identified = sum(1 for listing in raw if listing.get("_identified_by"))
        previous_backlog = phcache.backlog(pc)
        previous_oldest = min(previous_backlog.values(), default=None)
        queue_note = (
            f"; {len(previous_backlog)} previously deferred"
            + (f" since {previous_oldest}" if previous_oldest else "")
            if previous_backlog else ""
        )
        print(
            f"  photo queue: {len(critical_urls)} correctness-critical, "
            f"{len(raw) - len(critical_urls) - identified} history-only"
            f"{queue_note}"
        )
        budget_min = float(os.environ.get("RENTGEN_PHOTO_BUDGET_MIN", "90"))
        photo_stats.update(photomatch.attach_hashes(
            photo_queue, session=net.probe_session(), cache=pc, today=today,
            budget_s=budget_min * 60 if budget_min > 0 else None,
            critical_urls=critical_urls,
        ))
        deferred_urls = photo_stats.pop("deferred_urls")
        photo_stats["backlog"] = phcache.update_backlog(
            pc, deferred_urls, today)
        pruned = phcache.prune(pc, today)
        phcache.save(CACHE_PATH, pc)
        print(f"  phash cache: {len(pc.get('entries', {}))} urls "
              f"({pruned} pruned as stale)")
        if photo_stats["backlog"]["count"]:
            print(
                f"  photo backlog: {photo_stats['backlog']['count']} URLs "
                f"(oldest {photo_stats['backlog']['oldest']}); "
                f"{photo_stats['critical_deferred']} correctness-critical"
            )
    phase_seconds["photos"] = round(time.monotonic() - photo_started, 1)

    dedupe_started = time.monotonic()
    archived_raw = [x for x in raw if x.get("archived")]
    raw = [x for x in raw if not x.get("archived")]

    listings = dedupe(
        raw,
        allow_heuristic_fallback=photo_stats["heuristic_fallback_enabled"],
    )
    require_unique_urls(listings, "deduplicated properties")
    phase_seconds["dedupe"] = round(time.monotonic() - dedupe_started, 1)
    history_started = time.monotonic()

    hist_path = DATA_DIR / "history.json.gz"
    records = history.compact(history.load(hist_path))
    active_urls = {o.get("url") for l in listings for o in l.get("offers", [])}
    active_urls |= {l.get("url") for l in listings}
    active_urls.discard(None)

    n_arch = history.observe_archived(archived_raw, records, today)
    if archived_raw:
        print(f"  archived ads ingested into history: {n_arch}/{len(archived_raw)}")
    phase_seconds["history_prepare"] = round(
        time.monotonic() - history_started, 1)
    if verify_max > 0:
        sweep_min = float(os.environ.get("RENTGEN_DELIST_BUDGET_MIN", "10"))
        delist_started = time.monotonic()
        delist.sweep(records, today, net.probe_session(),
                     active_urls=active_urls, max_checks=verify_max,
                     budget_s=sweep_min * 60 if sweep_min > 0 else None)
        phase_seconds["delist"] = round(time.monotonic() - delist_started, 1)

    history_update_started = time.monotonic()
    history.update(listings, records, today)
    overrides.apply(records, overrides.load())
    phase_seconds["history_update"] = round(
        time.monotonic() - history_update_started, 1)

    rcn_stats = None
    snap = None
    rcn_health = {"status": "disabled", "fetched": None, "counts": {}, "error": None}
    rcn_started = time.monotonic()
    if rcn_mode != "0":
        teryt = REGION_CONFIG["teryt"]
        with net.rcn_session() as rcn_http:
            snap = rcn.refresh(RCN_CACHE, rcn_http, teryt_prefix=teryt, today=today,
                               force=(rcn_mode == "force"))
        rcn_health = rcn.refresh.last_health
        if snap is None:
            raise RuntimeError("No usable RCN snapshot; refusing to publish without transaction evidence")
        if snap:
            rcn.match(records, snap)
            rcn_stats = rcnstats.build(snap, records, today)
            rcn_stats["source"] = rcn_health
    history.reenrich(listings)
    phase_seconds["rcn"] = round(time.monotonic() - rcn_started, 1)

    geo_started = time.monotonic()
    geocoded = 0
    if os.environ.get("RENTGEN_GEO", "1") != "0":
        gc = geo.load(GEO_CACHE)
        _, geocoded = geo.attach(
            listings, gc, session=http, today=today,
            max_new=int(os.environ.get("RENTGEN_GEO_MAX", "500")),
            teryt_prefix=REGION_CONFIG["teryt"])
        geo.save(GEO_CACHE, gc)
    phase_seconds["geo"] = round(time.monotonic() - geo_started, 1)

    write_started = time.monotonic()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    history.save(hist_path, records)
    if pending_archive_state is not None:
        nieruchomosci_online.save_archive_state(NOL_ARCHIVE_STATE, pending_archive_state)
    link_same_size(listings)
    relisted = sum(1 for l in listings if l.get("relisted"))

    listings.sort(key=lambda l: (l.get("created") or ""), reverse=True)
    for p in listings:
        p.pop("phashes", None)

    archive = history.build_archive(records)
    payload.build(listings, DATA_DIR, archive=archive)
    (DATA_DIR / "listings.json").unlink(missing_ok=True)

    if rcn_stats:
        (DATA_DIR / "rcnstats.json").write_text(
            json.dumps(rcn_stats, ensure_ascii=False, indent=0), encoding="utf-8")

    mstats = marketstats.build(records, snap, today)
    mstats["rcn_health"] = rcn_health
    (DATA_DIR / "stats.json").write_text(
        json.dumps(mstats, ensure_ascii=False, indent=0), encoding="utf-8")

    by_source = {}
    for x in raw:
        by_source[x["source"]] = by_source.get(x["source"], 0) + 1

    phase_seconds["write"] = round(time.monotonic() - write_started, 1)
    phase_seconds["total"] = round(time.monotonic() - run_started, 1)
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
        "rcn_health": rcn_health,
        "rcn_stats": {"towns": len(rcn_stats["towns"]),
                      "gap_pairs": (rcn_stats["gap"].get("all") or {}).get("n", 0)}
                     if rcn_stats else None,
        "sold_confirmed": sum(1 for a in archive if a.get("sold")),
        "health": cov_summary["status"],
        "coverage": cov_summary,
        "photos": photo_stats,
        "runtime": {"seconds": phase_seconds["total"],
                    "phases": phase_seconds},
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
