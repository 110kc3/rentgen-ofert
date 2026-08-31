"""Canonical voivodeship catalog shared by the scraper and the site.

The source of truth is :mod:`site/regions.json`.  Portal paths must be read
from the catalog explicitly: similar-looking slugs are data, not a convention
the scrapers are allowed to assume.  This module also provides the cheap
workflow gate used before a requested region reaches a branch name or path.
"""
from __future__ import annotations

import argparse
import functools
import json
import pathlib
import re
from collections.abc import Mapping


ROOT = pathlib.Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "site" / "regions.json"
PORTALS = ("otodom", "olx", "gratka", "morizon")
CADENCES = {"manual", "twice_daily", "daily", "weekly"}
SLUG_RE = re.compile(r"^[a-z]+(?:-[a-z]+)*$")
PORTAL_SLUG_RE = re.compile(r"^[a-z]+(?:-{1,2}[a-z]+)*$")
TERYT_RE = re.compile(r"^\d{2}$")

# Poland assigns the 16 voivodeships the even two-digit prefixes 02..32. The
# slug-to-prefix mapping itself exists only in the catalog; this set merely
# catches a missing/duplicated/typoed official prefix.
OFFICIAL_TERYT_PREFIXES = {f"{number:02d}" for number in range(2, 33, 2)}


class RegionCatalogError(ValueError):
    """The catalog or a requested regional configuration is invalid."""


def _require(condition, message):
    if not condition:
        raise RegionCatalogError(message)


def _text(value, field, slug=None):
    where = f" for {slug!r}" if slug else ""
    _require(isinstance(value, str) and value.strip(),
             f"region field {field!r}{where} must be a non-empty string")


def _validate_region(entry, number):
    _require(isinstance(entry, dict), f"regions[{number}] must be an object")
    slug = entry.get("slug")
    _text(slug, "slug")
    _require(bool(SLUG_RE.fullmatch(slug)),
             f"invalid canonical region slug: {slug!r}")
    for field in ("label", "adjective", "locative"):
        _text(entry.get(field), field, slug)

    teryt = entry.get("teryt")
    _require(isinstance(teryt, str) and bool(TERYT_RE.fullmatch(teryt)),
             f"invalid two-digit TERYT prefix for {slug!r}: {teryt!r}")
    _require(isinstance(entry.get("enabled"), bool),
             f"enabled for {slug!r} must be boolean")
    _require(entry.get("cadence") in CADENCES,
             f"invalid cadence for {slug!r}: {entry.get('cadence')!r}")

    portals = entry.get("portals")
    _require(isinstance(portals, dict),
             f"portals for {slug!r} must be an object")
    _require(set(portals) == set(PORTALS),
             f"portals for {slug!r} must contain exactly: {', '.join(PORTALS)}")
    for portal in PORTALS:
        value = portals[portal]
        _require(isinstance(value, str)
                 and bool(PORTAL_SLUG_RE.fullmatch(value)),
                 f"invalid {portal} slug for {slug!r}: {value!r}")

    anchor = entry.get("anchor")
    if anchor is not None:
        _require(isinstance(anchor, dict),
                 f"anchor for {slug!r} must be an object")
        _text(anchor.get("name"), "anchor.name", slug)
        _text(anchor.get("genitive"), "anchor.genitive", slug)
        ll = anchor.get("ll")
        _require(isinstance(ll, list) and len(ll) == 2
                 and all(isinstance(v, (int, float)) and not isinstance(v, bool)
                         for v in ll),
                 f"anchor.ll for {slug!r} must be [lat, lon]")
        _require(-90 <= ll[0] <= 90 and -180 <= ll[1] <= 180,
                 f"anchor.ll for {slug!r} is outside WGS84 bounds")

    districts = entry.get("districts", {})
    _require(isinstance(districts, dict)
             and all(isinstance(k, str) and k and isinstance(v, str) and v
                     for k, v in districts.items()),
             f"districts for {slug!r} must map names to parent localities")


def load_catalog(path=CATALOG_PATH) -> dict:
    """Load and fully validate a catalog JSON file."""
    source = pathlib.Path(path)
    try:
        document = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise RegionCatalogError(f"cannot read region catalog {source}: {exc}") from exc

    _require(isinstance(document, dict), "region catalog must be an object")
    _require(document.get("schema") == 1, "region catalog schema must be 1")
    entries = document.get("regions")
    _require(isinstance(entries, list), "region catalog regions must be an array")
    _require(len(entries) == len(OFFICIAL_TERYT_PREFIXES),
             f"region catalog must contain exactly {len(OFFICIAL_TERYT_PREFIXES)} regions")

    for number, entry in enumerate(entries):
        _validate_region(entry, number)
    slugs = [entry["slug"] for entry in entries]
    teryts = [entry["teryt"] for entry in entries]
    _require(len(slugs) == len(set(slugs)), "region catalog slugs must be unique")
    _require(len(teryts) == len(set(teryts)), "region catalog TERYT prefixes must be unique")
    actual = {entry["slug"]: entry["teryt"] for entry in entries}
    _require(set(actual.values()) == OFFICIAL_TERYT_PREFIXES,
             "region catalog TERYT prefixes do not match the 16 voivodeships")
    default = document.get("default")
    _require(default in actual, f"unknown default region: {default!r}")
    _require(next(e for e in entries if e["slug"] == default)["enabled"],
             "default region must be enabled")
    return document


@functools.lru_cache(maxsize=1)
def catalog() -> dict:
    """Return the validated production catalog (cached for this process)."""
    return load_catalog(CATALOG_PATH)


def get_region(slug: str, document: Mapping | None = None) -> dict:
    """Return one canonical region or fail with an operator-friendly error."""
    source = catalog() if document is None else document
    for entry in source.get("regions", ()):
        if entry.get("slug") == slug:
            return entry
    known = ", ".join(entry["slug"] for entry in source.get("regions", ()))
    raise RegionCatalogError(f"unknown region {slug!r}; known regions: {known}")


def portal_slug(region: str, portal: str, document: Mapping | None = None) -> str:
    """Resolve one portal's explicit path slug for a canonical region."""
    if portal not in PORTALS:
        raise RegionCatalogError(f"unknown portal {portal!r}; expected one of {PORTALS}")
    return get_region(region, document)["portals"][portal]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="validate the regional catalog")
    parser.add_argument("path", nargs="?", default=str(CATALOG_PATH))
    parser.add_argument("--region", help="also validate a requested canonical slug")
    parser.add_argument("--require-enabled", action="store_true",
                        help="reject a known region whose enabled flag is false")
    args = parser.parse_args(argv)
    try:
        document = load_catalog(args.path)
        entry = get_region(args.region, document) if args.region else None
        if entry and args.require_enabled and not entry["enabled"]:
            raise RegionCatalogError(
                f"region {entry['slug']!r} is disabled in site/regions.json")
    except RegionCatalogError as exc:
        parser.error(str(exc))
    if entry:
        print(f"region catalog: {entry['slug']} (TERYT {entry['teryt']}, "
              f"cadence {entry['cadence']})")
    else:
        print(f"region catalog: {len(document['regions'])} regions, "
              f"default {document['default']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
