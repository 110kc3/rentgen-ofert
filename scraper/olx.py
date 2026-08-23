"""OLX scraper — region-wide sale listings (RENTGEN_REGION).

OLX embeds its search state in a `window.__PRERENDERED_STATE__ = "..."`
assignment where the value is a JSON string that has itself been JSON-encoded
(double-encoded), so it is decoded twice.

Ads that OLX syndicates from a partner portal (notably Otodom, partner code
``otodom_pl``) are skipped here because they are already collected directly
from Otodom - this removes the largest source of cross-portal duplicates.
"""
from __future__ import annotations

import json
import os
import re
import time

import requests

from . import bands, coverage
from .normalize import olx_rooms, to_float, to_int

# Whole-voivodeship search by default; override with RENTGEN_REGION.
REGION = os.environ.get("RENTGEN_REGION", "slaskie")
PATHS = {"house": "domy", "flat": "mieszkania"}


def search_url(typ: str, where: str) -> str:
    """The location is one slug in a fixed path position, so the same builder
    makes a region search and a town search — which is what subdivision needs.
    Verified on the sibling portals reachable from a dev machine:
    `gratka.pl/nieruchomosci/domy/gliwice` and `morizon.pl/domy/gliwice/` both
    answer with that town's listings from the region URL's slug position."""
    return f"https://www.olx.pl/nieruchomosci/{PATHS[typ]}/sprzedaz/{where}/"


SEARCH = {typ: search_url(typ, REGION) for typ in PATHS}

# OLX stops paginating long before it runs out of ads — the region search dies
# at page 25 whatever `totalPages` claims. That is not our cap and no amount of
# RENTGEN_MAX_PAGES fixes it; the only way to see the rest is to ask narrower
# questions, so an overflowing search is re-run per town and merged.
HARD_PAGE_CAP = 25
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
# escape-aware: the state is a JSON-encoded string, so a `\";` sequence inside it
# (an escaped quote followed by a semicolon in some ad text) must not end the match
_STATE = re.compile(r'__PRERENDERED_STATE__\s*=\s*"((?:[^"\\]|\\.)*)";', re.S)


def extract_state(html: str) -> dict:
    m = _STATE.search(html)
    if not m:
        raise ValueError("OLX: __PRERENDERED_STATE__ not found")
    return json.loads(json.loads('"' + m.group(1) + '"'))


_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)
# Words a bot wall puts on the page it serves instead of the results. Lowercase
# substrings, matched against the whole body — the challenge vendors change
# their markup far more often than they change these.
# ("cloudflare" itself is NOT one: plenty of ordinary pages load a CF asset,
# and a false "you were blocked" is exactly the wrong answer to hand item 3.)
CHALLENGE_MARKERS = ("captcha", "datadome", "cf-chl", "just a moment",
                     "attention required", "access denied", "are you a human",
                     "verify you are human", "unusual traffic", "zablokowan")
# Something only a real OLX page carries. Present + no state blob = OLX really
# did re-skin; absent = we were served something that is not OLX's search page.
OLX_MARKERS = ("olx.pl", "olxcdn", "__NEXT_DATA__", "prerendered")


def fingerprint(resp) -> str:
    """What we were actually served, for a page with no state blob in it.

    A missing `__PRERENDERED_STATE__` used to be logged as "layout changed?",
    which is a guess — and on 2026-08-11 it was the wrong one twice: OLX
    answered page 1 of both searches that way 50 seconds after the previous run
    had walked 518 of its pages, which is a block wearing a layout-change
    error message. The two need different fixes (slow down vs. rewrite the
    parser), so the run log has to be able to tell them apart on its own: this
    Pi cannot re-probe OLX (it 403s us) and CI keeps nothing but the log.
    """
    html = resp.text or ""
    low = html.lower()
    m = _TITLE.search(html)
    title = " ".join(m.group(1).split())[:80] if m else None
    challenge = [w for w in CHALLENGE_MARKERS if w in low]
    olx = [w for w in OLX_MARKERS if w.lower() in low]
    return (f"HTTP {getattr(resp, 'status_code', '?')}, {len(html)} B, "
            f"title={title!r}, challenge={challenge or 'none'}, "
            f"olx-markers={olx or 'none'}")


def _params(ad) -> dict:
    return {p["key"]: (p.get("normalizedValue") or p.get("value"))
            for p in ad.get("params", [])}


def parse_ads(ads, typ: str):
    out = []
    for ad in ads:
        partner = (ad.get("partner") or {}).get("code")
        if partner or ad.get("externalUrl"):
            continue  # syndicated (e.g. Otodom) -> collected at the source
        price = ((ad.get("price") or {}).get("regularPrice") or {})
        if not price.get("value"):
            continue  # "free"/"exchange"/price-on-request ads
        pm = _params(ad)
        loc = ad.get("location") or {}
        photos = ad.get("photos") or []
        user = ad.get("user") or {}
        is_business = bool(ad.get("isBusiness"))
        out.append({
            "source": "olx",
            "source_id": str(ad.get("id")),
            "url": ad.get("url"),
            "title": ad.get("title"),
            "type": typ,
            "price": price.get("value"),
            "area": to_float(pm.get("m")),
            "price_per_m2": to_int(pm.get("price_per_m")),
            "rooms": olx_rooms(pm.get("rooms")),
            "plot_area": to_float(pm.get("area")) if typ == "house" else None,
            "floor": pm.get("floor_select"),
            "locality": loc.get("cityName"),
            "district": loc.get("districtName"),
            "street": None,
            "is_private": not is_business,
            "market": (str(pm.get("market")).lower() if pm.get("market") else None),
            "agency": user.get("name") if is_business else None,
            "image": photos[0] if photos else None,
            "created": ad.get("lastRefreshTime") or ad.get("createdTime"),
            "also_on": [],
        })
    return out


def _walk(base_url, typ, tag, max_pages, delay, session, log, seen, out, extra=""):
    """Page through one search (optionally price-banded). Returns its cov row."""
    page = 1
    got = 0
    served = 0             # ads OLX handed over, before our own filtering
    served_keys = set()
    kept_keys = set()
    total_pages = None
    visible = None          # ads OLX says match the search   (5 503 for śląskie flats)
    servable = None         # ads OLX will actually hand over (1 000 — its cap)
    stopped = coverage.OK
    error = None
    http_status = None
    while page <= max_pages:
        url = f"{base_url}?page={page}" + (f"&{extra}" if extra else "")
        try:
            r = session.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
        except Exception as exc:  # keep what we have, stop this search
            log(f"  olx {typ}/{tag} page {page} error: {exc}")
            stopped = coverage.ERROR
            error, http_status = coverage.error_details(exc)
            break
        try:
            state = extract_state(r.text)
            listing = state["listing"]["listing"]
        except Exception as exc:
            # 200 OK with no results in it: say what the page WAS, so a block
            # and a re-skin are distinguishable from the log alone.
            log(f"  olx {typ}/{tag} page {page} error: {exc} — {fingerprint(r)}")
            stopped = coverage.ERROR
            error, http_status = coverage.error_details(exc)
            if http_status is None:
                http_status = getattr(r, "status_code", None)
            break
        ads = listing.get("ads", [])
        served += len(ads)
        served_keys.update(coverage.listing_key(
            typ, ad.get("id") or ad.get("url")) for ad in ads)
        parsed = parse_ads(ads, typ)
        kept_keys.update(coverage.listing_key(
            typ, a.get("source_id") or a.get("url")) for a in parsed)
        batch = [a for a in parsed if a["url"] not in seen]
        for a in batch:
            seen.add(a["url"])
        out.extend(batch)
        got += len(batch)
        total_pages = listing.get("totalPages", 1) or 1
        visible = listing.get("visibleElements") or visible
        servable = listing.get("totalElements") or servable
        log(f"  olx {typ}/{tag} page {page}/{min(total_pages, max_pages)}: +{len(batch)}")
        if not ads:
            # An empty page is how OLX enforces its own limit: it keeps claiming
            # `totalPages` in the hundreds and just stops serving ads. Running
            # out for real means we reached the last page it claimed.
            page -= 1                     # the empty page held nothing
            # ...but an empty FIRST page with nothing matching at all is simply
            # an empty search — a village with no flats, a price band nothing
            # falls into. `totalPages` defaults to 1 there, so `1 > 0` used to
            # call it a refusal, `bands.overflows` read that as overflow, and
            # every empty half was bisected again to MAX_DEPTH. That was 1 890
            # of run 31367424054's 1 948 warnings and ~110 of OLX's 144 scrape
            # minutes, spent asking Kozy for its 1.4M flats. A real refusal
            # still states `visibleElements`, which is what tells them apart.
            if total_pages > page and not (page == 0 and not visible):
                stopped = coverage.PORTAL_CAP
            break
        if page >= min(total_pages, max_pages):
            if total_pages > max_pages:
                stopped = coverage.OUR_CAP
            break
        page += 1
        time.sleep(delay)
    # The cap OLX actually enforces is stated, not hit: for a region search it
    # answers `visibleElements: 5503` (ads matching) with `totalElements: 1000`
    # and `totalPages: 25` (ads it will serve). Walking those 25 pages therefore
    # looks like a completed search — which is why śląskie yielded 470 listings
    # and the town subdivision below never once fired. Measured 2026-08-08.
    if stopped == coverage.OK and visible and servable and visible > servable:
        stopped = coverage.PORTAL_CAP
    return coverage.row("olx", typ, tag, page, got, stopped,
                        portal_pages=total_pages, portal_total=visible,
                        served=served, served_keys=served_keys,
                        kept_keys=kept_keys, error=error,
                        http_status=http_status)


def _portal_blocked_on_first_request(row) -> bool:
    """A root-page 403 on a fresh run is a runner/IP block, not a search miss.

    OLX has returned this exact response for both property types on every
    GitHub-hosted run since 2026-08-11.  Retrying the same URL after a cooldown,
    then probing the other type, cannot distinguish or recover that state.
    """
    return (row.get("stopped") == coverage.ERROR
            and row.get("http_status") == 403
            and (row.get("pages") or 0) <= 1
            and coverage.unique_seen_by(row) == 0)


def scrape(max_pages: int = 50, delay: float = 0.7, session=None, log=print,
           types=("house", "flat"), towns=None, banded=True):
    """`towns`: {slug: display} used ONLY to subdivide a search that OLX refused
    to paginate. Subdivision is additive — the region results are kept and the
    per-town results merged into them by URL — so a wrong town slug costs one
    request and can never lose a listing we already had."""
    session = session or requests.Session()
    out = []
    cov = []
    # One retry budget for the whole portal — see bands.Pacer. It matters most
    # here: OLX has ~120 town searches, so a per-search cooldown with no budget
    # would be an hour of sleeping the run cannot afford.
    pacer = bands.Pacer("olx", delay=delay, log=log)
    requested_types = [typ for typ in PATHS if typ in types]
    for type_index, typ in enumerate(requested_types):
        seen = set()
        pacer.pause()
        # Keep the bounded retry for transient failures, but a first-request
        # 403 is the portal-wide runner block production has repeated for days.
        # It is terminal evidence: no cooldown, no second type, towns or bands.
        row = pacer.attempt(
            typ,
            lambda: _walk(SEARCH[typ], typ, REGION, max_pages,
                          delay, session, log, seen, out),
            retry_if=lambda r: not _portal_blocked_on_first_request(r))
        row["role"] = coverage.PARENT
        cov.append(row)
        if _portal_blocked_on_first_request(row):
            remaining = requested_types[type_index + 1:]
            skipped = f"; skipping {', '.join(remaining)}" if remaining else ""
            log(f"  olx portal probe returned HTTP 403 on {typ} page 1 — "
                f"stopping the portal for this run{skipped}")
            for skipped_typ in remaining:
                reason = (f"OLX {skipped_typ} skipped after the {typ} portal "
                          f"probe returned HTTP 403")
                cov.append(coverage.row(
                    "olx", skipped_typ, REGION, 0, 0, coverage.ERROR,
                    role=coverage.PARENT, error=reason, http_status=403,
                    served_keys=set(), kept_keys=set(), skipped=True,
                    skip_reason=reason))
            break
        if row["stopped"] != coverage.PORTAL_CAP:
            continue
        # Two independent axes, and OLX needs both: towns cut the region into
        # ~60 pieces but a big city's own search hits the same 1 000-ad cap, and
        # price cuts every one of them further. Both are additive into `seen`.
        if towns:
            log(f"  olx {typ}: region search capped at page {row['pages']} of "
                f"{row.get('portal_pages')} — subdividing into {len(towns)} towns")
        for slug in (towns or {}):
            pacer.pause()                  # a town is a search, not a page
            town_row = pacer.attempt(slug, lambda s=slug: _walk(
                search_url(typ, s), typ, s, max_pages, delay, session, log,
                seen, out))
            town_row["role"] = coverage.SUPPLEMENT
            cov.append(town_row)
            if banded and bands.overflows(town_row, "olx"):
                rows, _ = bands.subdivide(
                    "olx",
                    lambda lo, hi, btag, s=slug: _walk(
                        search_url(typ, s), typ, f"{s}/{btag}", max_pages, delay,
                        session, log, seen, out, bands.qs("olx", lo, hi)),
                    log=log, pacer=pacer)
                for band_row in rows:
                    band_row["role"] = coverage.SUPPLEMENT
                cov.extend(rows)
        if banded:
            # …and band the region search itself, so a region whose town list is
            # empty (a brand-new one) still gets past the cap.
            rows, seeds = bands.subdivide(
                "olx",
                lambda lo, hi, btag: _walk(SEARCH[typ], typ, btag, max_pages,
                                           delay, session, log, seen, out,
                                           bands.qs("olx", lo, hi)),
                log=log, pacer=pacer)
            cov.extend(rows)
            totals_ok = bands.check_totals(
                "olx", typ, row.get("portal_total"), seeds, log=log)
            bands.record_partition(row, seeds, totals_ok)
    scrape.last_coverage = cov
    return out
