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
              "portal_cap" the portal refused to paginate further
              "error"      the request or the parse failed

main.py folds these into meta.json's `coverage` block and prints a warning for
anything that is not "end", so truncation is visible in the run log and in the
published data instead of having to be inferred from suspiciously round counts.

`portal_pages` / `portal_total` are filled in when the portal states them
(otodom and olx report `totalPages`; gratka/morizon only reveal the end by
404ing), which is what makes "is the cap still binding?" answerable per run.
"""
from __future__ import annotations

OK = "end"
OUR_CAP = "cap"
PORTAL_CAP = "portal_cap"
ERROR = "error"

TRUNCATED = (OUR_CAP, PORTAL_CAP, ERROR)


def row(source, typ, tag, pages, listings, stopped,
        portal_pages=None, portal_total=None) -> dict:
    out = {"source": source, "type": typ, "pages": pages,
           "listings": listings, "stopped": stopped}
    if tag and tag != typ:
        out["tag"] = tag
    if portal_pages is not None:
        out["portal_pages"] = portal_pages
    if portal_total is not None:
        out["portal_total"] = portal_total
    return out


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
    """Compact per-source view for meta.json, plus the truncated searches."""
    by_source = {}
    for r in rows or ():
        s = by_source.setdefault(r["source"], {"searches": 0, "pages": 0,
                                               "listings": 0, "truncated": 0})
        s["searches"] += 1
        s["pages"] += r.get("pages") or 0
        s["listings"] += r.get("listings") or 0
        s["truncated"] += 1 if r.get("stopped") in TRUNCATED else 0
    return {
        "by_source": by_source,
        "truncated": [r for r in rows or () if r.get("stopped") in TRUNCATED],
    }


def warnings(rows) -> list:
    """Human lines for the run log — one per search that did not finish."""
    out = []
    for r in rows or ():
        st = r.get("stopped")
        if st not in TRUNCATED:
            continue
        where = f"{r['source']} {r['type']}" + (f"/{r['tag']}" if r.get("tag") else "")
        if st == OUR_CAP:
            extra = ""
            if r.get("portal_pages"):
                extra = f" of {r['portal_pages']} the portal has"
            out.append(f"  !! {where}: stopped at our page cap ({r['pages']}{extra})"
                       f" — raise RENTGEN_MAX_PAGES or subdivide the search")
        elif st == PORTAL_CAP:
            out.append(f"  !! {where}: portal refused to paginate past page "
                       f"{r['pages']} — subdivision is the only way to see the rest")
        else:
            out.append(f"  !! {where}: failed after {r['pages']} page(s)")
    return out
