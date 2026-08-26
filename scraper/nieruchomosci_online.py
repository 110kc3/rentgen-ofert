"""nieruchomosci-online.pl scraper — one sub-domain per town.

Each town is a sub-domain (e.g. ``pyskowice.nieruchomosci-online.pl``) whose
result pages embed a schema.org ``CollectionPage`` JSON-LD block. Rental
listings are skipped. The portal orders current offers before archived
("OutOfStock"/"SoldOut") offers, so normal runs stop after a confirmed
archive-only boundary. A less-frequent full harvest returns archived records
with ``archived: True`` — main.py keeps them out of the dashboard but feeds
them to the history store as evidence the ad ended (likely sold).

Unlike the other four portals this one has no region-wide search, so it needs a
town list per region. Town-level request/current/archive/stop statistics are
published explicitly; a capped town must never disappear inside a two-row
source aggregate.

Where that list comes from (probed 2026-08-08): **not** from the portal. It
publishes no sitemap (`/sitemap.xml` 404s, robots.txt declares none) and its
region landing pages name no towns at all, so there is nothing to harvest.
Instead `resolve_towns()` derives it from the localities the other four portals
already returned for the region — real towns, correctly spelled, ranked by how
many listings each has — and caches the result. Śląskie keeps a hand-curated
seed list so its behaviour is unchanged and a cold run is never worse than
before. A sub-domain that does not exist costs one request and is skipped
(see scrape()), so an over-generous list is cheap and a short one is not.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import re
import time
from collections import Counter

import requests

from . import coverage
from .normalize import take_unseen, to_float, to_int
from .rcn import _fold

# Cap the town list: each town costs at least one request per type, and the tail
# of villages is already covered by the other portals' region-wide searches.
MAX_TOWNS = int(os.environ.get("RENTGEN_NOL_TOWNS", "60"))

# The live/current results precede the archive. Two consecutive archive-only
# pages make the boundary robust to one malformed availability page while still
# avoiding the ~1,400 archive pages the old twice-daily walk consumed.
ACTIVE_ARCHIVE_ONLY_PAGES = max(1, int(
    os.environ.get("RENTGEN_NOL_ARCHIVE_BOUNDARY_PAGES", "2")))
ARCHIVE_STATE_SCHEMA = 1

# Hand-curated seed for śląskie: the cities with powiat rights plus major towns.
# slug -> proper display name. The slug loses Polish diacritics, so a derived
# `slug.title()` would leak fake localities like "Dabrowa-Gornicza" into the
# data and break locality-keyed dedupe/geocoding for offers without an address —
# hence display names are always carried alongside, never reconstructed.
SEED_TOWNS = {
    "slaskie": {
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
    },
}


def slugify(name: str) -> str:
    """Display name -> sub-domain slug, the way the portal spells it:
    'Dąbrowa Górnicza' -> 'dabrowa-gornicza', 'Bielsko-Biała' -> 'bielsko-biala'.
    Verified against every entry of the śląskie seed list (see tests)."""
    return "-".join(_fold(name).split())


def load_towns(cache_path) -> dict:
    """Cached {region: {slug: display}} — survives a run where a portal failed."""
    try:
        return json.loads(pathlib.Path(cache_path).read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}


def save_towns(cache_path, cache: dict):
    p = pathlib.Path(cache_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(cache, ensure_ascii=False, indent=0, sort_keys=True),
                   encoding="utf-8")
    os.replace(tmp, p)


def _state_from_meta(meta_path) -> dict:
    """Bootstrap archive cadence from the last pre-split production output.

    The first run after this feature ships has no dedicated marker yet, but the
    previous ``meta.json`` came from a full archive walk. Reusing its date/counts
    avoids paying for another identical 1,700-page harvest immediately.
    """
    try:
        meta = json.loads(pathlib.Path(meta_path).read_text(encoding="utf-8"))
    except (FileNotFoundError, TypeError, ValueError):
        return {}
    source = (((meta.get("coverage") or {}).get("by_source") or {})
              .get("nieruchomosci-online") or {})
    refreshed = str(meta.get("updated") or "")[:10]
    if not refreshed or not source:
        return {}

    issues = [i for i in (meta.get("coverage") or {}).get("issues", [])
              if i.get("source") == "nieruchomosci-online"]
    by_type = {}
    for typ, summary in (source.get("types") or {}).items():
        capped = sorted({town for issue in issues if issue.get("type") == typ
                         for town in issue.get("capped_partitions", [])})
        failed = sorted({town for issue in issues if issue.get("type") == typ
                         for town in issue.get("failed_partitions", [])})
        by_type[typ] = {
            "current": int(summary.get("current") or 0),
            "archived": int(summary.get("archived") or 0),
            "pages": int(summary.get("pages") or 0),
            "capped": capped,
            "failed": failed,
        }
    return {
        "schema": ARCHIVE_STATE_SCHEMA,
        "refreshed": refreshed,
        "records": sum(v["archived"] for v in by_type.values()),
        "complete": not any(v["capped"] or v["failed"]
                            for v in by_type.values()),
        "by_type": by_type,
        "bootstrapped_from_meta": True,
    }


def load_archive_state(path, meta_path=None) -> dict:
    try:
        state = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        return state if state.get("schema") == ARCHIVE_STATE_SCHEMA else {}
    except (FileNotFoundError, TypeError, ValueError):
        return _state_from_meta(meta_path) if meta_path else {}


def save_archive_state(path, state: dict):
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1,
                              sort_keys=True), encoding="utf-8")
    os.replace(tmp, p)


def archive_due(state: dict, today, mode="auto", interval_days=7) -> bool:
    """Whether this run should walk past the current/archive boundary.

    ``mode`` accepts ``auto`` (default cadence), ``force``/``1`` and
    ``skip``/``0``. Invalid operator input fails before any portal request.
    """
    mode = str(mode or "auto").strip().lower()
    if mode in {"force", "refresh", "1", "true", "yes"}:
        return True
    if mode in {"skip", "off", "0", "false", "no"}:
        return False
    if mode != "auto":
        raise ValueError("RENTGEN_NOL_ARCHIVE must be auto, force or skip")
    try:
        refreshed = dt.date.fromisoformat(str(state.get("refreshed")))
    except (TypeError, ValueError):
        return True
    current = (today if isinstance(today, dt.date)
               else dt.date.fromisoformat(str(today)))
    return (current - refreshed).days >= max(0, int(interval_days))


def archive_state_from_rows(rows, today) -> dict:
    by_type = {}
    for row in rows:
        by_type[row["type"]] = {
            "current": int(row.get("current") or 0),
            "archived": int(row.get("archived") or 0),
            "pages": int(row.get("pages") or 0),
            "capped": list(row.get("capped_partitions") or ()),
            "failed": list(row.get("failed_partitions") or ()),
        }
    return {
        "schema": ARCHIVE_STATE_SCHEMA,
        "refreshed": str(today),
        "records": sum(v["archived"] for v in by_type.values()),
        "complete": bool(rows) and not any(
            v["capped"] or v["failed"] for v in by_type.values())
            and not any(row.get("unknown") for row in rows),
        "by_type": by_type,
    }


def resolve_towns(region, listings, cache_path=None, max_towns=None) -> dict:
    """{slug: display} for `region`: the hand-curated seed, plus the towns the
    other portals just found (busiest first), plus whatever a previous run
    cached. Capped at `max_towns`; the cache is refreshed as a side effect.

    `listings` are the raw dicts already collected this run — main.py scrapes
    this portal last precisely so they are available on the very first run in a
    new region, with no bootstrap pass needed.
    """
    max_towns = MAX_TOWNS if max_towns is None else max_towns
    cache = load_towns(cache_path) if cache_path else {}
    towns = dict(cache.get(region) or {})
    towns.update(SEED_TOWNS.get(region) or {})       # seed always wins on spelling

    counts = Counter()
    names = {}
    for l in listings or ():
        loc = (l.get("locality") or "").strip()
        # Portals sometimes put a POWIAT in the locality field — always the
        # lowercase adjectival form ('cieszyński', 'tarnogórski': 17 of them,
        # 2 586 listings in śląskie). They are not towns, have no sub-domain,
        # and every real town name is capitalised, so the case is the filter.
        if not loc or not loc[:1].isupper():
            continue
        slug = slugify(loc)
        if not slug:
            continue
        counts[slug] += 1
        names.setdefault(slug, loc)
    for slug, _ in counts.most_common():
        towns.setdefault(slug, names[slug])

    # Stable priority: the curated seed's declared order, then towns observed in
    # this region's current source results (inventory desc, slug tie-break), then
    # cached fallbacks. This keeps cold-region bootstrap deterministic without
    # letting small count fluctuations reorder the known seed on every run.
    seed = SEED_TOWNS.get(region) or {}
    ranked = list(seed)
    ranked.extend(s for s, _ in sorted(counts.items(),
                                       key=lambda item: (-item[1], item[0]))
                  if s not in seed)
    ranked.extend(s for s in towns if s not in seed and s not in counts)
    ranked = list(dict.fromkeys(ranked))[:max_towns]
    out = {s: towns[s] for s in ranked}

    if cache_path:
        cache[region] = out
        save_towns(cache_path, cache)
    return out


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


def parse_offers(offers, typ: str, town: str = "", towns: dict = None):
    """`town` is the sub-domain slug; `towns` maps it to the display name. The
    slug is never title-cased into a locality — that would invent spellings
    like "Dabrowa-Gornicza" and split dedupe/geocoding keys."""
    display = (towns or {}).get(town)
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
            "locality": addr.get("addressLocality") or display,
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
           types=("house", "flat"), towns=None, harvest_archive=True,
           archive_state=None, today=None, archive_only_pages=None):
    """`towns`: {slug: display} from resolve_towns(). Defaults to the region's
    seed list so the module still works standalone.

    Normal pipeline runs pass ``harvest_archive=False`` and stop after two
    archive-only result pages. A forced/cadenced full harvest keeps the legacy
    behavior and returns archive rows for history ingestion.
    """
    if towns is None:
        towns = SEED_TOWNS.get(os.environ.get("RENTGEN_REGION", "slaskie")) or {}
    archive_only_pages = (ACTIVE_ARCHIVE_ONLY_PAGES if archive_only_pages is None
                          else max(1, int(archive_only_pages)))
    today = today or dt.date.today().isoformat()
    session = session or requests.Session()
    out = []
    cov = []
    for typ, path in PATHS.items():
        if typ not in types:
            continue
        seen = set()
        served_keys = set()
        kept_keys = set()
        pages_total = 0
        got = 0
        capped_towns = []
        current = 0
        archived = 0
        succeeded_towns = 0
        failed_towns = []
        first_error = None
        first_http_status = None
        town_coverage = {}
        for town in towns:
            base = f"https://{town}.nieruchomosci-online.pl/{path}/"
            page = 1
            dup_pages = 0
            archive_pages = 0
            town_succeeded = False
            town_stop = "end"
            town_stats = {
                "requests": 0, "pages": 0,
                "served_current": 0, "served_archived": 0,
                "new_current": 0, "new_archived": 0,
            }
            while page <= max_pages:
                url = base if page == 1 else f"{base}?p={page}"
                town_stats["requests"] += 1
                try:
                    r = session.get(url, headers=HEADERS, timeout=30)
                    r.raise_for_status()
                    all_batch = parse_offers(
                        extract_offers(r.text), typ, town, towns)
                except Exception as exc:  # missing sub-domain etc. -> skip town
                    log(f"  nieruchomosci-online {typ}/{town} page {page} error: {exc}")
                    error, http_status = coverage.error_details(exc)
                    # A derived town without a portal sub-domain is a clean
                    # empty partition. Refusals and parser/server failures are
                    # coverage defects and must not masquerade as zero stock.
                    if http_status == 404:
                        if not town_succeeded:
                            succeeded_towns += 1
                            town_succeeded = True
                        town_stop = "empty" if page == 1 else "end"
                    else:
                        failed_towns.append(town)
                        town_stop = "error"
                        town_stats["http_status"] = http_status
                        if first_error is None:
                            first_error, first_http_status = error, http_status
                    break
                if not town_succeeded:
                    succeeded_towns += 1
                    town_succeeded = True
                town_stats["pages"] += 1
                current_batch = [b for b in all_batch if not b.get("archived")]
                archived_batch = [b for b in all_batch if b.get("archived")]
                town_stats["served_current"] += len(current_batch)
                town_stats["served_archived"] += len(archived_batch)
                batch = all_batch if harvest_archive else current_batch
                served_keys.update(coverage.listing_key(
                    typ, b.get("source_id") or b.get("url")) for b in batch)
                kept_keys.update(coverage.listing_key(
                    typ, b.get("source_id") or b.get("url")) for b in batch)
                # Key on the AD ID, not the URL. Every town subdomain serves its
                # neighbours' offers under its own hostname, so the same ad
                # arrives as gliwice.…/26859971.html and katowice.…/26859971.html
                # — distinct URLs, one property. Keying on the URL made every
                # page look fresh, which (a) inflated the count 5x (58 613 rows
                # collapsing to 11 172 properties in the 2026-08-08 run) and
                # (b) meant the `dup_pages` exit below could never fire, so
                # every town was walked to the cap. That was 75 of the run's
                # 123 scrape minutes, spent to gain 83 listings.
                fresh = take_unseen(batch, seen, key="source_id")
                out.extend(fresh)
                got += len(fresh)
                fresh_current = sum(1 for b in fresh if not b.get("archived"))
                fresh_archived = len(fresh) - fresh_current
                current += fresh_current
                archived += fresh_archived
                town_stats["new_current"] += fresh_current
                town_stats["new_archived"] += fresh_archived
                if fresh:
                    log(f"  nieruchomosci-online {typ}/{town} page {page}: +{len(fresh)}")
                if not all_batch:
                    town_stop = "end"
                    break              # empty result page = past the end
                if not harvest_archive and not current_batch:
                    archive_pages += 1
                    if archive_pages >= archive_only_pages:
                        town_stop = "archive_boundary"
                        log(f"  nieruchomosci-online {typ}/{town}: current offers "
                            f"ended before page {page - archive_only_pages + 1}; "
                            "archive deferred")
                        break
                    if page >= max_pages:
                        capped_towns.append(town)
                        town_stop = "cap"
                        break
                    page += 1
                    time.sleep(delay)
                    continue
                archive_pages = 0
                if not fresh:
                    # towns cross-list each other's offers, so a page can be all
                    # already-seen URLs while later pages still hold new ones —
                    # only stop after two such pages in a row (also bounds the
                    # portals that echo the last page forever when paged past it)
                    dup_pages += 1
                    if dup_pages >= 2:
                        town_stop = "duplicate_boundary"
                        break
                else:
                    dup_pages = 0
                if page >= max_pages:
                    capped_towns.append(town)
                    town_stop = "cap"
                    break
                page += 1
                time.sleep(delay)
            town_stats["stop"] = town_stop
            pages_total += town_stats["pages"]
            town_coverage[town] = town_stats
        # one row per type, not per town: 60 towns x 2 types would bury the
        # other portals in meta.json, and the towns share one budget anyway
        stopped = (coverage.ERROR if failed_towns else
                   coverage.OUR_CAP if capped_towns else coverage.OK)
        cov_row = coverage.row(
            "nieruchomosci-online", typ, f"{len(towns)} towns", pages_total, got,
            stopped,
            served_keys=served_keys, kept_keys=kept_keys,
            current=current, archived=archived,
            error=first_error, http_status=first_http_status)
        cov_row["partition_axis"] = "town"
        cov_row["partitions_total"] = len(towns)
        cov_row["partitions_succeeded"] = succeeded_towns
        cov_row["towns"] = town_coverage
        if failed_towns:
            cov_row["failed_partitions"] = failed_towns
            cov_row["partial_success"] = succeeded_towns > 0
        if capped_towns:
            cov_row["capped_partitions"] = capped_towns
        if not towns:
            cov_row["unknown"] = True
        cov.append(cov_row)
    if harvest_archive:
        archive_state = archive_state_from_rows(cov, today)
    else:
        archive_state = dict(archive_state or {})
    for row in cov:
        cached = (archive_state.get("by_type") or {}).get(row["type"], {})
        info = {"mode": "refresh" if harvest_archive else
                ("cached" if archive_state.get("refreshed") else "not_available")}
        if archive_state.get("refreshed"):
            info["refreshed"] = archive_state["refreshed"]
            info["records"] = int(cached.get("archived") or 0)
            info["complete"] = bool(archive_state.get("complete"))
        row["archive_harvest"] = info
    scrape.last_archive_state = archive_state
    scrape.last_coverage = cov
    return out
