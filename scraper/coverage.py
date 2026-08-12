"""Did a search return everything, or did it stop early?

A region-wide search is capped twice: by `RENTGEN_MAX_PAGES` (ours) and by
whatever the portal will serve (theirs). Both truncate silently — you get a
plausible-looking pile of listings and no hint that more exist. That is exactly
what happened here: with the old default of 50 pages, EVERY paginated portal
was stopping on our cap inside a single voivodeship (gratka/morizon/otodom at
page 50, olx at 25), and nothing said so.

Each scraper records one row per search it runs:

    {source, type, tag, pages, listings, stopped, portal_pages, portal_total}

    stopped = "end"        the portal ran out (404 / empty page / last page)
              "cap"        WE stopped it — RENTGEN_MAX_PAGES was reached
              "portal_cap" the portal refused to serve the rest
              "error"      the request or the parse failed

main.py folds these into meta.json's `coverage` block and prints a warning for
anything that is not "end", so truncation is visible in the run log and in the
published data instead of having to be inferred from suspiciously round counts.

**Every portal states how many ads it holds — that is the ground truth this
module is built around**, because a stop reason alone lies. Measured 2026-08-08:
gratka's śląskie flat search 404s past page 200, which the loop reads as "ran
out" while gratka's own header says 9 856 ads and 200 pages is 7 000. Without
the stated total, that truncation is invisible; with it, it is arithmetic.

    otodom   pagination.totalItems (18 505) + totalPages (515) — exact
    gratka   "9856 ogłoszeń" in the meta description — exact
    morizon  "ponad 9000 ogłoszeń" — a LOWER BOUND, it rounds to 1000s
    olx      visibleElements (5 503) vs totalElements (1 000 = its own cap)

`total_is_min` marks the morizon case: `collected < portal_total` still proves
truncation (the real total is at least that), but `collected > portal_total`
proves nothing and must never be flagged.

`covered()` compares collected against the stated total. It is a FLOOR, not a
percentage of listings shown to the user: each scraper filters as it parses
(otodom drops INVESTMENT bundles, olx drops ads syndicated from Otodom and
price-on-request ones), so a complete search legitimately lands below 100%.
Treat a big gap as "look here", not as a defect count.
"""
from __future__ import annotations

OK = "end"
OUR_CAP = "cap"
PORTAL_CAP = "portal_cap"
ERROR = "error"

TRUNCATED = (OUR_CAP, PORTAL_CAP, ERROR)

# How far below the portal's own count a search may land before we call it
# truncated. Slack absorbs ads that vanish mid-crawl and the portals' own
# counter drift; it is nowhere near the gaps real truncation produces
# (gratka: 7 000 of 9 856 = 71%).
COMPLETE_ENOUGH = 0.95


def row(source, typ, tag, pages, listings, stopped,
        portal_pages=None, portal_total=None, total_is_min=False,
        served=None, scout=False) -> dict:
    out = {"source": source, "type": typ, "pages": pages,
           "listings": listings, "stopped": stopped}
    if scout:
        # Stopped on purpose, with price bands queued up behind it to cover the
        # same ground properly (see otodom.SCOUT_PAGES). Still truncated as a
        # search — it stays in the `truncated` count, which is factual — but it
        # is not advice-worthy, so `warnings` keeps quiet about it.
        out["scout"] = True
    if served is not None and served != listings:
        out["served"] = served
    if tag and tag != typ:
        out["tag"] = tag
    if portal_pages is not None:
        out["portal_pages"] = portal_pages
    if portal_total is not None:
        out["portal_total"] = portal_total
        if total_is_min:
            out["total_is_min"] = True
    return out


def seen_by(r) -> int:
    """Ads the portal actually handed over for a search, before OUR filters.

    This, not the kept count, is what a stated total must be compared against.
    OLX states `visibleElements` for everything matching the search but we drop
    the ads it syndicates from Otodom (collected at the source) — on a town
    search that is most of them, so comparing kept-vs-stated declared every one
    of ~60 town searches truncated. The 2026-08-08 run printed 126 such
    warnings, nearly all false, which is an excellent way to stop reading them.
    """
    served = r.get("served")
    return r.get("listings") if served is None else served


def short_of_total(collected, portal_total, tolerance=COMPLETE_ENOUGH) -> bool:
    """Did this search return materially less than the portal says it holds?

    Answers False when the portal states nothing — an unknown total is not
    evidence of completeness, which is why the scrapers keep their own stop
    reasons as well.
    """
    if not portal_total or collected is None:
        return False
    return collected < portal_total * tolerance


def covered(collected, portal_total):
    """Collected as a percentage of the portal's stated total (see module doc:
    this is a floor). None when the portal states no total."""
    if not portal_total or collected is None:
        return None
    return round(100.0 * collected / portal_total, 1)


def stop_reason(page, max_pages, total_pages=None, hit_end=False) -> str:
    """Why a paginating loop ended.

    `page` is the last page actually fetched. A loop that walked to our cap
    while the portal still had pages left stopped on OUR limit; one that ran out
    of results stopped on the portal's end.
    """
    if hit_end:
        return OK
    if total_pages is not None and page >= total_pages:
        return OK
    if page >= max_pages:
        return OUR_CAP
    return OK


def summarise(rows) -> dict:
    """Compact per-source view for meta.json, plus the truncated searches.

    `portal_total` / `pct` per source are what make two runs comparable: "did
    the coverage work help?" is one number, not a diff of stop reasons.
    """
    by_source = {}
    for r in rows or ():
        s = by_source.setdefault(r["source"], {"searches": 0, "pages": 0,
                                               "listings": 0, "seen": 0,
                                               "truncated": 0})
        s["searches"] += 1
        s["pages"] += r.get("pages") or 0
        s["listings"] += r.get("listings") or 0
        s["seen"] += seen_by(r) or 0
        s["truncated"] += 1 if r.get("stopped") in TRUNCATED else 0
        if r.get("portal_total"):
            s["portal_total"] = s.get("portal_total", 0) + r["portal_total"]
            # one search of the source lacking an exact total makes the whole
            # source's total a lower bound
            if r.get("total_is_min"):
                s["total_is_min"] = True
    for s in by_source.values():
        # `pct` answers "how much of the portal did we get to see", so it counts
        # what was served. What we kept is `listings`; the gap is our own
        # filtering (syndicated ads, INVESTMENT bundles), not missed coverage.
        pct = covered(s["seen"], s.get("portal_total"))
        if pct is not None:
            s["pct"] = pct
        if s["seen"] == s["listings"]:
            del s["seen"]
    return {
        "by_source": by_source,
        "truncated": [r for r in rows or () if r.get("stopped") in TRUNCATED],
    }


def _where(r) -> str:
    return f"{r['source']} {r['type']}" + (f"/{r['tag']}" if r.get("tag") else "")


def _of_total(r) -> str:
    """' — 7000 of 9856 (71.0%)' when the portal states its own count."""
    total = r.get("portal_total")
    if not total:
        return ""
    approx = "≥" if r.get("total_is_min") else ""
    seen = seen_by(r)
    kept = "" if seen == r.get("listings") else f", kept {r.get('listings')}"
    return (f" — collected {seen} of {approx}{total}"
            f" ({covered(seen, total)}%){kept}")


def warnings(rows) -> list:
    """Human lines for the run log — one per search that did not finish."""
    out = []
    for r in rows or ():
        st = r.get("stopped")
        if st not in TRUNCATED:
            # A search can stop for an innocent-looking reason and still be
            # truncated — gratka 404s past page 200 exactly like it 404s past
            # its last page. The stated total is the only thing that tells
            # those two apart, so it gets the last word.
            if short_of_total(seen_by(r), r.get("portal_total")):
                out.append(f"  !! {_where(r)}: search ended cleanly but short of "
                           f"the portal's own count{_of_total(r)} — subdivide it")
            continue
        if st == OUR_CAP and r.get("scout"):
            # "raise RENTGEN_MAX_PAGES or subdivide the search" is exactly what
            # a scout pass has already done. The bands that follow report their
            # own coverage, and fall short loudly enough on their own.
            continue
        if st == OUR_CAP:
            extra = ""
            if r.get("portal_pages"):
                extra = f" of {r['portal_pages']} the portal has"
            out.append(f"  !! {_where(r)}: stopped at our page cap ({r['pages']}"
                       f"{extra}){_of_total(r)}"
                       f" — raise RENTGEN_MAX_PAGES or subdivide the search")
        elif st == PORTAL_CAP:
            out.append(f"  !! {_where(r)}: portal refused to serve past page "
                       f"{r['pages']}{_of_total(r)}"
                       f" — subdivision is the only way to see the rest")
        else:
            out.append(f"  !! {_where(r)}: failed after {r['pages']} page(s)")
    return out
