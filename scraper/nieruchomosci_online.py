"""nieruchomosci-online.pl scraper — one sub-domain per town.

Each town is a sub-domain (e.g. ``pyskowice.nieruchomosci-online.pl``) whose
result pages embed a schema.org ``CollectionPage`` JSON-LD block. Rental
listings are skipped; archived ("OutOfStock"/"SoldOut") listings are returned
with ``archived: True`` — main.py keeps them out of the dashboard but feeds
them to the history store as evidence the ad ended (likely sold).

Unlike the other four portals this one has no region-wide search, so it needs a
town list per region — which is also why it is the ONLY portal not silently
truncated by a pagination cap (see TODO.md, whole-Poland plan).

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

import json
import os
import pathlib
import re
import time
from collections import Counter

import requests

from . import coverage
from .normalize import to_float, to_int
from .rcn import _fold

# Cap the town list: each town costs at least one request per type, and the tail
# of villages is already covered by the other portals' region-wide searches.
MAX_TOWNS = int(os.environ.get("RENTGEN_NOL_TOWNS", "60"))

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

    # rank: seeded towns first (curated = certainly real), then by listing count
    seed = SEED_TOWNS.get(region) or {}
    ranked = sorted(towns, key=lambda s: (s not in seed, -counts[s], s))[:max_towns]
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
           types=("house", "flat"), towns=None):
    """`towns`: {slug: display} from resolve_towns(). Defaults to the region's
    seed list so the module still works standalone."""
    if towns is None:
        towns = SEED_TOWNS.get(os.environ.get("RENTGEN_REGION", "slaskie")) or {}
    session = session or requests.Session()
    out = []
    cov = []
    for typ, path in PATHS.items():
        if typ not in types:
            continue
        seen = set()
        pages_total = 0
        got = 0
        capped = 0
        for town in towns:
            base = f"https://{town}.nieruchomosci-online.pl/{path}/"
            page = 1
            dup_pages = 0
            while page <= max_pages:
                url = base if page == 1 else f"{base}?p={page}"
                try:
                    r = session.get(url, headers=HEADERS, timeout=30)
                    r.raise_for_status()
                    batch = parse_offers(extract_offers(r.text), typ, town, towns)
                except Exception as exc:  # missing sub-domain etc. -> skip town
                    log(f"  nieruchomosci-online {typ}/{town} page {page} error: {exc}")
                    break
                # Key on the AD ID, not the URL. Every town subdomain serves its
                # neighbours' offers under its own hostname, so the same ad
                # arrives as gliwice.…/26859971.html and katowice.…/26859971.html
                # — distinct URLs, one property. Keying on the URL made every
                # page look fresh, which (a) inflated the count 5x (58 613 rows
                # collapsing to 11 172 properties in the 2026-08-08 run) and
                # (b) meant the `dup_pages` exit below could never fire, so
                # every town was walked to the cap. That was 75 of the run's
                # 123 scrape minutes, spent to gain 83 listings.
                fresh = [b for b in batch if b["source_id"] not in seen]
                for b in fresh:
                    seen.add(b["source_id"])
                out.extend(fresh)
                got += len(fresh)
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
                if page > max_pages:
                    capped += 1       # a town with more pages than we allowed
            pages_total += page - 1
        # one row per type, not per town: 60 towns x 2 types would bury the
        # other portals in meta.json, and the towns share one budget anyway
        cov.append(coverage.row(
            "nieruchomosci-online", typ, f"{len(towns)} towns", pages_total, got,
            coverage.OUR_CAP if capped else coverage.OK))
    scrape.last_coverage = cov
    return out
