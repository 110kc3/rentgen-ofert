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

Rows also name their role in the enumeration:

    direct       an exhaustive strategy with no parent/child relationship
    parent       the one search whose portal_total defines the inventory
    partition    a disjoint price slice replacing an overflowing parent
    supplement   an overlapping fallback (for example an OLX town search)

That distinction is load-bearing. The old summary added an unbanded parent and
all of its price-band children into both numerator and denominator. A failed
band then removed its total from the denominator, so coverage could improve
when the scrape got worse (and Morizon's lower bound reached 103%). Schema v2
keeps the parent total exactly once and unions internal listing identities
across every additive search. Parent and child rows can overlap freely without
double-counting.

main.py folds these into meta.json's `coverage` block, emits explicit source +
region health, and prints a warning for every *actionable* incomplete leaf.
Parents intentionally replaced by partitions remain diagnostic rows but are no
longer presented as work the operator forgot to do.

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

`covered()` compares unique served identities against the one parent total. It
is a FLOOR, not a percentage of listings shown to the user: each scraper filters as it parses
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

DIRECT = "direct"
PARENT = "parent"
PARTITION = "partition"
SUPPLEMENT = "supplement"

HEALTHY = "healthy"
PARTIAL = "partial"
BLOCKED = "blocked"
UNKNOWN = "unknown"

# How far below the portal's own count a search may land before we call it
# truncated. Slack absorbs ads that vanish mid-crawl and the portals' own
# counter drift; it is nowhere near the gaps real truncation produces
# (gratka: 7 000 of 9 856 = 71%).
COMPLETE_ENOUGH = 0.95


def listing_key(typ: str, value) -> str | None:
    """Stable, type-scoped identity kept only while coverage is summarised."""
    if value is None:
        return None
    text = str(value).strip()
    return f"{typ}:{text}" if text else None


def error_details(exc) -> tuple[str | None, int | None]:
    """Short public error text + HTTP status, if requests exposed one."""
    if exc is None:
        return None, None
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    text = " ".join(str(exc).split())[:240] or exc.__class__.__name__
    if status is None:
        # Fake sessions and a few wrappers preserve the useful status only in
        # their message. Do not mistake arbitrary three-digit numbers for HTTP.
        import re
        match = re.search(r"(?:HTTP\s*)?([45]\d\d)(?:\s|\b)", text, re.I)
        status = int(match.group(1)) if match else None
    return text, status


def row(source, typ, tag, pages, listings, stopped,
        portal_pages=None, portal_total=None, total_is_min=False,
        served=None, scout=False, role=DIRECT, served_keys=None,
        kept_keys=None, current=None, archived=None, error=None,
        http_status=None) -> dict:
    out = {"source": source, "type": typ, "pages": pages,
           "listings": listings, "stopped": stopped}
    if role != DIRECT:
        out["role"] = role
    if scout:
        # Stopped on purpose, with price bands queued up behind it to cover the
        # same ground properly (see otodom.SCOUT_PAGES). It remains a diagnostic
        # row, but is neither an actionable issue nor a warning.
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
    if current is not None:
        out["current"] = current
    if archived is not None:
        out["archived"] = archived
    if error:
        out["error"] = str(error)[:240]
    if http_status is not None:
        out["http_status"] = int(http_status)
    # Sets are intentionally private: main.py needs them to union overlapping
    # parent/band/town searches, but public_row() strips them before JSON output.
    if served_keys is not None:
        out["_served_keys"] = frozenset(k for k in served_keys if k is not None)
    if kept_keys is not None:
        out["_kept_keys"] = frozenset(k for k in kept_keys if k is not None)
    return out


def public_row(r: dict) -> dict:
    """JSON-safe coverage row (private identity sets removed)."""
    return {k: v for k, v in r.items() if not k.startswith("_")}


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


def unique_seen_by(r) -> int:
    """Unique identities served by one search, falling back for v1 rows."""
    if "_served_keys" in r:
        return len(r.get("_served_keys") or ())
    return seen_by(r)


def unique_kept_by(r) -> int:
    """Unique parsed identities in one search, before cross-search dedupe."""
    if "_kept_keys" in r:
        return len(r.get("_kept_keys") or ())
    return r.get("listings") or 0


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
    """Collected as a bounded percentage of the portal's stated total.

    A lower-bound total (Morizon) can be smaller than the unique ads actually
    served. Completeness cannot exceed 100%; ``total_is_min`` remains alongside
    the number to say that 100 means "at least the declared floor".
    """
    if not portal_total or collected is None:
        return None
    return round(min(100.0, max(0.0, 100.0 * collected / portal_total)), 1)


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


def _role(r):
    return r.get("role") or DIRECT


def _replaced(r) -> bool:
    """A non-terminal diagnostic row whose narrower children own coverage."""
    return bool(r.get("scout")
                or (_role(r) == PARENT and r.get("partitioned"))
                or (_role(r) == PARTITION and r.get("replaced")))


def _issue(r) -> str | None:
    """Actionable leaf defect, or None for intentional/overlapping rows."""
    if _role(r) == SUPPLEMENT or _replaced(r):
        return None
    stopped = r.get("stopped")
    if stopped == ERROR:
        return "error"
    if stopped == OUR_CAP:
        return "our_cap"
    if stopped == PORTAL_CAP:
        return "portal_cap"
    if short_of_total(unique_seen_by(r), r.get("portal_total")):
        return "short_total"
    return None


def _fallback_accounting_rows(rows):
    """Non-overlapping rows used only by old/manual callers without identities."""
    leaves = [r for r in rows if _role(r) == PARTITION and not r.get("replaced")]
    if leaves:
        return leaves
    roots = [r for r in rows if _role(r) in (PARENT, DIRECT)]
    return roots or [r for r in rows if _role(r) != SUPPLEMENT]


def _unique_count(rows, private_key, count_fn) -> int:
    with_ids = [r for r in rows if private_key in r]
    if with_ids:
        keys = set()
        for r in with_ids:
            keys.update(r.get(private_key) or ())
        return len(keys)
    return sum(count_fn(r) or 0 for r in _fallback_accounting_rows(rows))


def _listing_counts(listings, source, typ):
    selected = [l for l in (listings or ())
                if l.get("source") == source and l.get("type") == typ]
    if not selected:
        return None
    keys = {listing_key(typ, l.get("source_id") or l.get("url"))
            for l in selected}
    keys.discard(None)
    current = sum(1 for l in selected if not l.get("archived"))
    archived = len(selected) - current
    return len(keys) if keys else len(selected), current, archived


def _inventory_total(rows):
    """The portal total once: parent/direct rows, never their partitions."""
    parents = [r for r in rows if _role(r) == PARENT and r.get("portal_total")]
    owners = parents or [r for r in rows
                         if _role(r) == DIRECT and r.get("portal_total")]
    if not owners:
        return None, False
    return (sum(r["portal_total"] for r in owners),
            any(r.get("total_is_min") for r in owners))


def _partition_summary(rows, parents):
    parts = [r for r in rows if _role(r) == PARTITION]
    if not parts:
        return None
    leaves = [r for r in parts if not r.get("replaced")]
    failed = [r.get("tag") or r.get("partition", {}).get("label")
              for r in leaves if r.get("stopped") == ERROR]
    capped = [r.get("tag") or r.get("partition", {}).get("label")
              for r in leaves if r.get("stopped") in (OUR_CAP, PORTAL_CAP)]
    missing = [r.get("tag") or r.get("partition", {}).get("label")
               for r in leaves if r.get("stopped") == ERROR and not unique_seen_by(r)]
    out = {
        "axis": "price",
        "leaves": len(leaves),
        "complete": sum(1 for r in leaves if _issue(r) is None),
        "failed": [x for x in failed if x],
        "capped": [x for x in capped if x],
        "missing": [x for x in missing if x],
    }
    unaccounted = sum(p.get("partition_unaccounted") or 0 for p in parents)
    if unaccounted:
        out["unaccounted"] = unaccounted
    return out


def _type_summary(source, typ, rows, listings=None):
    parents = [r for r in rows if _role(r) == PARENT]
    total, total_is_min = _inventory_total(rows)
    served_unique = _unique_count(rows, "_served_keys", seen_by)
    kept_unique = _unique_count(rows, "_kept_keys",
                                lambda r: r.get("listings") or 0)

    listed = _listing_counts(listings, source, typ)
    if listed is not None:
        kept_unique, current, archived = listed
    else:
        explicit_current = [r.get("current") for r in rows
                            if r.get("current") is not None]
        explicit_archived = [r.get("archived") for r in rows
                             if r.get("archived") is not None]
        current = sum(explicit_current) if explicit_current else kept_unique
        archived = sum(explicit_archived) if explicit_archived else 0

    issue_rows = [(r, _issue(r)) for r in rows]
    issue_rows = [(r, issue) for r, issue in issue_rows if issue]
    partition_bad = any(p.get("partition_total_ok") is False for p in parents)
    pct = covered(served_unique, total)

    roots = [r for r in rows if _role(r) in (PARENT, DIRECT)]
    root_unknown = bool(roots) and all(r.get("unknown") for r in roots)
    root_failed = (bool(roots)
                   and all(r.get("stopped") == ERROR for r in roots)
                   and not any(r.get("partial_success") for r in roots))
    reasons = []
    if root_unknown and kept_unique == 0:
        status = UNKNOWN
        reasons.append("no_partitions_resolved")
    elif root_failed and kept_unique == 0:
        status = BLOCKED
        reasons.append("root_search_failed")
    else:
        if issue_rows:
            reasons.append("incomplete_searches")
        if partition_bad:
            reasons.append("partition_total_shortfall")
        if total and pct is not None and pct < COMPLETE_ENOUGH * 100:
            reasons.append("coverage_shortfall")
        status = PARTIAL if reasons else HEALTHY

    out = {
        "status": status,
        "searches": len(rows),
        "pages": sum(r.get("pages") or 0 for r in rows),
        "served_unique": served_unique,
        "kept_unique": kept_unique,
        "current": current,
        "archived": archived,
        "issues": len(issue_rows),
    }
    if reasons:
        out["reasons"] = reasons
    if total is not None:
        out["portal_total"] = total
        out["pct"] = pct
        if total_is_min:
            out["total_is_min"] = True
    partitions = _partition_summary(rows, parents)
    if partitions:
        out["partitions"] = partitions
    statuses = sorted({r.get("http_status") for r, _ in issue_rows
                       if r.get("http_status") is not None})
    if statuses:
        out["http_statuses"] = statuses
    return out, issue_rows


def _combined_status(statuses):
    statuses = list(statuses)
    if not statuses:
        return UNKNOWN
    if all(s == BLOCKED for s in statuses):
        return BLOCKED
    if any(s in (PARTIAL, BLOCKED) for s in statuses):
        return PARTIAL
    if any(s == UNKNOWN for s in statuses):
        return UNKNOWN
    return HEALTHY


def _unknown_type_summary(source, typ, listings=None):
    listed = _listing_counts(listings, source, typ)
    kept, current, archived = listed or (0, 0, 0)
    return {
        "status": UNKNOWN, "searches": 0, "pages": 0,
        "served_unique": 0, "kept_unique": kept,
        "current": current, "archived": archived, "issues": 0,
        "reasons": ["no_coverage_rows"],
    }


def summarise(rows, listings=None, expected_sources=None, expected_types=None) -> dict:
    """Schema-v2 source/region health with non-overlapping completeness.

    ``listings`` is the authoritative scraper output before archived records
    are split away. Search rows carry private identity sets for the unique
    served numerator; those sets never enter the returned JSON.
    """
    rows = list(rows or ())
    sources = set(expected_sources or ()) | {r["source"] for r in rows}
    by_source = {}
    public_issues = []

    for source in sorted(sources):
        src_rows = [r for r in rows if r["source"] == source]
        types = sorted(set(expected_types or ()) | {r["type"] for r in src_rows})
        if not types:
            by_source[source] = {
                "status": UNKNOWN, "searches": 0, "pages": 0,
                "listings": 0, "served_unique": 0, "kept_unique": 0,
                "current": 0, "archived": 0, "truncated": 0, "issues": 0,
                "reasons": ["no_coverage_rows"], "types": {},
            }
            continue

        type_summaries = {}
        src_issue_rows = []
        for typ in types:
            typ_rows = [r for r in src_rows if r["type"] == typ]
            if typ_rows:
                summary, issues = _type_summary(
                    source, typ, typ_rows, listings)
            else:
                summary, issues = _unknown_type_summary(
                    source, typ, listings), []
            type_summaries[typ] = summary
            src_issue_rows.extend(issues)

        status = _combined_status(t["status"] for t in type_summaries.values())
        current = sum(t["current"] for t in type_summaries.values())
        archived = sum(t["archived"] for t in type_summaries.values())
        kept_unique = sum(t["kept_unique"] for t in type_summaries.values())
        served_unique = sum(t["served_unique"] for t in type_summaries.values())
        declared = [t for t in type_summaries.values() if t.get("portal_total")]
        portal_total = sum(t["portal_total"] for t in declared)
        served_declared = sum(t["served_unique"] for t in declared)
        reasons = sorted({reason for t in type_summaries.values()
                          for reason in t.get("reasons", [])})

        src = {
            "status": status,
            "searches": len(src_rows),
            "pages": sum(r.get("pages") or 0 for r in src_rows),
            "listings": current,
            "served_unique": served_unique,
            "kept_unique": kept_unique,
            "current": current,
            "archived": archived,
            "truncated": len(src_issue_rows),
            "issues": len(src_issue_rows),
            "types": type_summaries,
        }
        if reasons:
            src["reasons"] = reasons
        if served_unique != current:
            src["seen"] = served_unique       # v1 compatibility for consumers
        if portal_total:
            src["portal_total"] = portal_total
            src["pct"] = covered(served_declared, portal_total)
            if any(t.get("total_is_min") for t in declared):
                src["total_is_min"] = True
            if len(declared) != len(type_summaries):
                src["total_scope"] = "partial"
        statuses = sorted({r.get("http_status") for r, _ in src_issue_rows
                           if r.get("http_status") is not None})
        if statuses:
            src["http_statuses"] = statuses
        by_source[source] = src

        for r, issue in src_issue_rows:
            item = public_row(r)
            item["issue"] = issue
            public_issues.append(item)

    region_status = _combined_status(s["status"] for s in by_source.values())
    # `truncated` remains as a compatibility alias, but now contains only
    # actionable terminal defects—not parents already replaced by bands.
    return {
        "schema": 2,
        "status": region_status,
        "by_source": by_source,
        "issues": public_issues,
        "truncated": public_issues,
    }


def _where(r) -> str:
    return f"{r['source']} {r['type']}" + (f"/{r['tag']}" if r.get("tag") else "")


def _of_total(r) -> str:
    """' — 7000 of 9856 (71.0%)' when the portal states its own count."""
    total = r.get("portal_total")
    if not total:
        return ""
    approx = "≥" if r.get("total_is_min") else ""
    seen = unique_seen_by(r)
    kept_count = unique_kept_by(r)
    kept = "" if seen == kept_count else f", kept {kept_count}"
    return (f" — collected {seen} of {approx}{total}"
            f" ({covered(seen, total)}%){kept}")


def warnings(rows) -> list:
    """Human lines for the run log — one per search that did not finish."""
    out = []
    for r in rows or ():
        # A parent/scout or overflowing intermediate partition is supposed to
        # stop early: its children are the implementation of the remedy. Only
        # terminal leaves can still require operator action.
        if _replaced(r):
            continue
        st = r.get("stopped")
        if st not in TRUNCATED:
            # A search can stop for an innocent-looking reason and still be
            # truncated — gratka 404s past page 200 exactly like it 404s past
            # its last page. The stated total is the only thing that tells
            # those two apart, so it gets the last word.
            if short_of_total(unique_seen_by(r), r.get("portal_total")):
                out.append(f"  !! {_where(r)}: search ended cleanly but short of "
                           f"the portal's own count{_of_total(r)} — subdivide it")
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
            status = f" (HTTP {r['http_status']})" if r.get("http_status") else ""
            out.append(f"  !! {_where(r)}: failed after {r['pages']} page(s){status}")
    return out
