"""Bounded, read-only inventory scout for every catalog region.

The production scraper is deliberately expensive: it paginates, subdivides,
downloads photos, updates caches and writes a regional data tree.  P3 needs a
smaller question first: does each configured region slug reach a real search
page, and how much inventory does that page declare?  This module asks at most
one page for each region-wide source and listing type and stores only aggregate
evidence.  It never calls the production scraper or writes under ``site/`` or
``cache/``.

Nieruchomosci-online is not part of this comparison.  It has no region-wide
search root; its production crawl is derived from town subdomains discovered
after the other sources have returned listings.  Choosing one arbitrary town
per region would produce misleading inventory measurements.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import time
from collections import Counter
from urllib.parse import unquote, urlsplit

import requests

from scraper import gratka, morizon, olx, otodom
from scraper.net import probe_session
from scraper.normalize import stated_total
from scraper.regions import PORTALS, load_catalog


SCHEMA = 1
TYPES = ("house", "flat")
REFUSAL_STATUSES = {403, 405, 429}
SOURCE_LABELS = {
    "otodom": "Otodom",
    "olx": "OLX",
    "gratka": "Gratka",
    "morizon": "Morizon",
}
HEADERS = {
    "otodom": otodom.HEADERS,
    "olx": olx.HEADERS,
    "gratka": gratka.HEADERS,
    "morizon": morizon.HEADERS,
}
EXCLUDED_SOURCES = [{
    "source": "nieruchomosci-online",
    "requests": 0,
    "reason": (
        "no region-wide search root; production derives town subdomains from "
        "listings returned by the four regional sources"
    ),
}]


def search_url(source: str, typ: str, slug: str) -> str:
    """Build a first-page URL without relying on import-time region state."""
    if typ not in TYPES:
        raise ValueError(f"unknown listing type: {typ!r}")
    if source == "otodom":
        estate = {"house": "dom", "flat": "mieszkanie"}[typ]
        return (f"{otodom.BASE}/pl/wyniki/sprzedaz/{estate}/{slug}"
                f"?page=1&limit={otodom.PAGE_SIZE}")
    if source == "olx":
        return f"{olx.search_url(typ, slug)}?page=1"
    if source == "gratka":
        estate = {"house": "domy", "flat": "mieszkania"}[typ]
        return f"{gratka.BASE}/nieruchomosci/{estate}/{slug}"
    if source == "morizon":
        estate = {"house": "domy", "flat": "mieszkania"}[typ]
        return f"{morizon.BASE}/{estate}/{slug}/"
    raise ValueError(f"unknown regional source: {source!r}")


def _integer(value, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field} is boolean, not an inventory count")
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} is not an integer: {value!r}") from exc
    if number < 0:
        raise ValueError(f"{field} is negative: {number}")
    return number


def parse_page(source: str, typ: str, html: str) -> dict:
    """Extract aggregate first-page evidence; never retain listing content."""
    if source == "otodom":
        search = otodom.extract_search_ads(html)
        items = search.get("items")
        pagination = search.get("pagination")
        if not isinstance(items, list) or not isinstance(pagination, dict):
            raise ValueError("Otodom search state lacks items or pagination")
        return {
            "declared_inventory": _integer(
                pagination.get("totalItems"), "Otodom totalItems"),
            "declared_is_minimum": False,
            "page_items": len(items),
            "servable_inventory": None,
        }

    if source in {"gratka", "morizon"}:
        parser = gratka.parse_cards if source == "gratka" else morizon.parse_cards
        cards = parser(html, typ)
        total, is_minimum = stated_total(html)
        # An empty, count-free document could be a consent wall or a new
        # layout.  Do not call it a valid zero-inventory search.
        if total is None and not cards:
            raise ValueError(f"{SOURCE_LABELS[source]} page has no cards or stated total")
        return {
            "declared_inventory": total,
            "declared_is_minimum": is_minimum,
            "page_items": len(cards),
            "servable_inventory": None,
        }

    if source == "olx":
        state = olx.extract_state(html)
        listing = ((state.get("listing") or {}).get("listing")
                   if isinstance(state, dict) else None)
        if not isinstance(listing, dict) or not isinstance(listing.get("ads"), list):
            raise ValueError("OLX state lacks listing ads")
        return {
            "declared_inventory": _integer(
                listing.get("visibleElements"), "OLX visibleElements"),
            "declared_is_minimum": False,
            "page_items": len(listing["ads"]),
            "servable_inventory": _integer(
                listing.get("totalElements"), "OLX totalElements"),
        }

    raise ValueError(f"unknown regional source: {source!r}")


def _short_error(exc: Exception) -> str:
    text = " ".join(str(exc).split())
    return f"{type(exc).__name__}: {text}"[:300]


def _challenge_page(html: str) -> bool:
    low = (html or "").lower()
    return any(marker in low for marker in olx.CHALLENGE_MARKERS)


def _final_url_keeps_slug(url: str, slug: str) -> bool:
    """A wrong slug often redirects to a national page that still parses."""
    path_parts = [part for part in unquote(urlsplit(url).path).split("/") if part]
    return slug in path_parts


def _target_row(source: str, typ: str, region: dict) -> dict:
    slug = region["portals"][source]
    return {
        "region": region["slug"],
        "teryt": region["teryt"],
        "enabled": region["enabled"],
        "source": source,
        "type": typ,
        "portal_slug": slug,
        "requested_url": search_url(source, typ, slug),
        "final_url": None,
        "redirected": False,
        "status": None,
        "http_status": None,
        "declared_inventory": None,
        "declared_is_minimum": False,
        "servable_inventory": None,
        "page_items": None,
        "elapsed_ms": None,
        "error": None,
    }


def probe(source: str, typ: str, region: dict, session, timeout: float,
          clock=time.monotonic) -> dict:
    """Make exactly one GET and classify its inventory/reachability evidence."""
    slug = region["portals"][source]
    row = _target_row(source, typ, region)
    url = row["requested_url"]
    started = clock()
    try:
        response = session.get(url, headers=HEADERS[source], timeout=timeout)
        row["http_status"] = getattr(response, "status_code", None)
        row["final_url"] = str(getattr(response, "url", None) or url)
        row["redirected"] = row["final_url"] != url
        status = row["http_status"]
        if status in REFUSAL_STATUSES:
            row["status"] = "blocked"
            row["error"] = f"HTTP {status} refusal"
            return row
        if status == 404:
            row["status"] = "not_found"
            row["error"] = "HTTP 404; configured slug or search path may be invalid"
            return row
        if not isinstance(status, int) or status >= 400:
            row["status"] = "http_error"
            row["error"] = f"HTTP {status}"
            return row
        if row["redirected"] and not _final_url_keeps_slug(row["final_url"], slug):
            row["status"] = "off_slug_redirect"
            row["error"] = "redirect target dropped the configured region slug"
            return row
        html = response.text or ""
        try:
            row.update(parse_page(source, typ, html))
        except Exception as exc:
            row["status"] = "blocked" if _challenge_page(html) else "parse_error"
            row["error"] = _short_error(exc)
            return row
        row["status"] = "ok"
        return row
    except requests.RequestException as exc:
        row["status"] = "network_error"
        row["error"] = _short_error(exc)
        return row
    finally:
        row["elapsed_ms"] = max(0, round((clock() - started) * 1000))


def skipped_probe(source: str, typ: str, region: dict, blocked_by: dict) -> dict:
    """Record a target suppressed after a source-wide refusal."""
    row = _target_row(source, typ, region)
    row.update({
        "status": "skipped_after_block",
        "http_status": blocked_by.get("http_status"),
        "elapsed_ms": 0,
        "error": (
            f"not requested after {source} was refused at "
            f"{blocked_by['region']}/{blocked_by['type']}"
        ),
    })
    return row


def budget_skipped_probe(source: str, typ: str, region: dict) -> dict:
    """Retain the target shape after the scout's wall-clock budget expires."""
    row = _target_row(source, typ, region)
    row.update({
        "status": "skipped_after_budget",
        "elapsed_ms": 0,
        "error": "not requested after the scout runtime budget expired",
    })
    return row


def _region_summary(
        regions: list[dict], probes: list[dict]) -> tuple[list[dict], list[str]]:
    summaries = []
    for region in regions:
        rows = [row for row in probes if row["region"] == region["slug"]]
        known = [row["declared_inventory"] for row in rows
                 if row["status"] == "ok"
                 and isinstance(row["declared_inventory"], int)]
        declared_targets = tuple(sorted(
            f"{row['source']}/{row['type']}" for row in rows
            if row["status"] == "ok"
            and isinstance(row["declared_inventory"], int)
        ))
        by_source = {}
        for source in PORTALS:
            source_rows = [row for row in rows if row["source"] == source]
            values = [row["declared_inventory"] for row in source_rows
                      if row["status"] == "ok"
                      and isinstance(row["declared_inventory"], int)]
            by_source[source] = {
                "declared_sum": sum(values) if values else None,
                "declared_probes": len(values),
                "minimum": any(row["declared_is_minimum"] for row in source_rows),
                "statuses": dict(sorted(Counter(
                    row["status"] for row in source_rows).items())),
            }
        summaries.append({
            "region": region["slug"],
            "label": region["label"],
            "teryt": region["teryt"],
            "enabled": region["enabled"],
            # This is a cross-source ranking signal, not a unique-listing
            # estimate: sources overlap, and Gratka/Morizon share inventory.
            "declared_sum": sum(known) if known else None,
            "declared_probes": len(known),
            "target_probes": len(PORTALS) * len(TYPES),
            "issue_probes": sum(row["status"] != "ok" for row in rows),
            "by_source": by_source,
            "_declared_targets": declared_targets,
        })

    # A source-wide refusal can make six declared targets the fair comparison
    # shape for every region. A one-region 404 must not be ranked beside that
    # shape merely because its partial sum happens to be large. Use the most
    # common exact set of successful source/type targets, and only rank rows
    # that match it. If no target produced a count, there is no ranking.
    signatures = Counter(row["_declared_targets"] for row in summaries)
    ranking_targets = min(
        signatures,
        key=lambda signature: (
            -signatures[signature], -len(signature), signature),
    ) if signatures else ()

    comparable = []
    incomplete = []
    for row in summaries:
        is_comparable = (
            bool(ranking_targets)
            and row["_declared_targets"] == ranking_targets
        )
        row["ranking_status"] = "comparable" if is_comparable else "incomplete"
        row["rank"] = None
        row.pop("_declared_targets")
        (comparable if is_comparable else incomplete).append(row)

    comparable.sort(key=lambda row: (
        -(row["declared_sum"] or 0), row["region"]))
    incomplete.sort(key=lambda row: (
        -row["declared_probes"], -(row["declared_sum"] or 0), row["region"]))
    for rank, row in enumerate(comparable, 1):
        row["rank"] = rank
    return comparable + incomplete, list(ranking_targets)


def _slug_checks(regions: list[dict], probes: list[dict]) -> list[dict]:
    checks = []
    for region in regions:
        for source in PORTALS:
            rows = [row for row in probes
                    if row["region"] == region["slug"] and row["source"] == source]
            statuses = {row["type"]: row["status"] for row in rows}
            if all(status == "ok" for status in statuses.values()):
                result = "reachable"
            elif statuses and all(status in {"not_found", "off_slug_redirect"}
                                  for status in statuses.values()):
                result = "bad_slug_candidate"
            elif any(status in {"not_found", "off_slug_redirect"}
                     for status in statuses.values()):
                result = "review"
            elif any(status in {"blocked", "skipped_after_block"}
                     for status in statuses.values()):
                result = "blocked"
            else:
                result = "inconclusive"
            checks.append({
                "region": region["slug"],
                "source": source,
                "portal_slug": region["portals"][source],
                "result": result,
                "statuses": statuses,
            })
    return checks


def scout(document: dict, session=None, timeout: float = 20.0,
          delay: float = 0.7, runtime_budget: float = 40 * 60,
          sleep=time.sleep, log=print, now=None, clock=time.monotonic) -> dict:
    """Run the complete bounded scout and return its serialisable report."""
    regions = document["regions"]
    targets = len(regions) * len(PORTALS) * len(TYPES)
    own_session = session is None
    session = session or probe_session()
    probes = []
    blocked_sources = {}
    requests_made = 0
    started = clock()
    budget_exhausted = False
    try:
        for region in regions:
            for source in PORTALS:
                for typ in TYPES:
                    if source in blocked_sources:
                        row = skipped_probe(
                            source, typ, region, blocked_sources[source])
                    elif clock() - started >= runtime_budget:
                        budget_exhausted = True
                        row = budget_skipped_probe(source, typ, region)
                    else:
                        row = probe(
                            source, typ, region, session, timeout, clock=clock)
                        requests_made += 1
                        if row["status"] == "blocked":
                            blocked_sources[source] = row
                    probes.append(row)
                    declared = row["declared_inventory"]
                    suffix = f", declared {declared:,}" if declared is not None else ""
                    log(f"[{len(probes):03d}/{targets}] {region['slug']} "
                        f"{source}/{typ}: {row['status']}{suffix}")
                    if requests_made and len(probes) < targets \
                            and not row["status"].startswith("skipped_after_"):
                        sleep(delay)
    finally:
        if own_session:
            session.close()

    generated = now or dt.datetime.now(dt.timezone.utc)
    if generated.tzinfo is None:
        generated = generated.replace(tzinfo=dt.timezone.utc)
    status_counts = dict(sorted(Counter(
        row["status"] for row in probes).items()))
    elapsed = max(0, round(clock() - started, 1))
    region_summaries, ranking_targets = _region_summary(regions, probes)
    return {
        "schema": SCHEMA,
        "generated_at": generated.astimezone(dt.timezone.utc).isoformat(
            timespec="seconds").replace("+00:00", "Z"),
        "scope": {
            "regions": len(regions),
            "sources": list(PORTALS),
            "types": list(TYPES),
            "pages_per_target": 1,
            "target_probes": targets,
            "request_budget": targets,
            "requests_made": requests_made,
            "retry_budget": 0,
            "runtime_budget_seconds": runtime_budget,
            "elapsed_seconds": elapsed,
            "runtime_budget_exhausted": budget_exhausted,
            "excluded_sources": EXCLUDED_SOURCES,
        },
        "summary": {
            "status_counts": status_counts,
            "ranking_declared_targets": ranking_targets,
            "regions": region_summaries,
            "slug_checks": _slug_checks(regions, probes),
        },
        "probes": probes,
    }


def _source_cell(row: dict, source: str) -> str:
    summary = row["by_source"][source]
    total = summary["declared_sum"]
    if total is not None:
        prefix = "≥" if summary["minimum"] else ""
        value = f"{prefix}{total:,}"
        if summary["declared_probes"] != len(TYPES):
            value += f" ({summary['declared_probes']}/{len(TYPES)})"
        return value
    return "/".join(summary["statuses"])


def markdown_summary(report: dict) -> str:
    """Compact Actions summary; the JSON artifact remains the evidence."""
    scope = report["scope"]
    statuses = ", ".join(
        f"{key} {value}" for key, value in report["summary"]["status_counts"].items())
    lines = [
        "# P3 nationwide one-page scout",
        "",
        (f"Generated `{report['generated_at']}`. Made **{scope['requests_made']}** "
         f"of at most **{scope['request_budget']}** requests with no retries; "
         f"target rows: **{scope['target_probes']}**."),
        (f"Elapsed: **{scope['elapsed_seconds']} s** of the "
         f"**{scope['runtime_budget_seconds']} s** runtime budget; exhausted: "
         f"**{'yes' if scope['runtime_budget_exhausted'] else 'no'}**."),
        "",
        ("Declared sums are ranking signals, not unique-listing estimates: "
         "portals overlap and Gratka/Morizon share inventory. Only regions "
         "matching the most common set of declared source/type targets receive "
         "a rank, provided that set is non-empty; `—` marks incomplete, "
         "non-comparable evidence. "
         "Per-source parentheses mark incomplete house/flat pairs; Morizon may "
         "publish a rounded lower bound."),
        "",
        ("Ranking targets: " + ", ".join(
            f"`{target}`" for target in
            report["summary"]["ranking_declared_targets"])
         if report["summary"]["ranking_declared_targets"]
         else "Ranking targets: none."),
        "",
        f"Statuses: {statuses}.",
        "",
        "| Rank | Region | Otodom | OLX | Gratka | Morizon | Known | Issues |",
        "|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report["summary"]["regions"]:
        rank = row["rank"] if row["rank"] is not None else "—"
        lines.append(
            f"| {rank} | {row['label']} (`{row['region']}`) "
            f"| {_source_cell(row, 'otodom')} | {_source_cell(row, 'olx')} "
            f"| {_source_cell(row, 'gratka')} | {_source_cell(row, 'morizon')} "
            f"| {row['declared_probes']}/{row['target_probes']} "
            f"| {row['issue_probes']} |")
    candidates = [row for row in report["summary"]["slug_checks"]
                  if row["result"] in {"bad_slug_candidate", "review"}]
    lines.extend(["", "## Slug review", ""])
    if candidates:
        for row in candidates:
            lines.append(
                f"- `{row['region']}` / `{row['source']}` / "
                f"`{row['portal_slug']}`: {row['result']} ({row['statuses']})")
    else:
        lines.append("No HTTP-404 slug candidate was observed.")
    lines.extend([
        "",
        "Nieruchomości-online was not probed: it has no region-wide search root.",
        "",
    ])
    return "\n".join(lines)


def write_report(report: dict, output, summary=None) -> None:
    output_path = pathlib.Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    if summary:
        summary_path = pathlib.Path(summary)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(markdown_summary(report), encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="run the bounded one-page scout for all 16 regions")
    parser.add_argument("--output", required=True,
                        help="JSON report path (use RUNNER_TEMP in CI)")
    parser.add_argument("--summary", help="optional Markdown summary path")
    parser.add_argument("--timeout", type=float, default=20.0,
                        help="per-request timeout in seconds (default: 20)")
    parser.add_argument("--delay", type=float, default=0.7,
                        help="delay between real requests in seconds (default: 0.7)")
    parser.add_argument("--runtime-budget-minutes", type=float, default=40.0,
                        help="stop starting requests after this many minutes (default: 40)")
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if args.delay < 0:
        parser.error("--delay cannot be negative")
    if args.runtime_budget_minutes <= 0:
        parser.error("--runtime-budget-minutes must be positive")

    report = scout(
        load_catalog(), timeout=args.timeout, delay=args.delay,
        runtime_budget=args.runtime_budget_minutes * 60)
    write_report(report, args.output, args.summary)
    print(f"scout report: {report['scope']['requests_made']}/"
          f"{report['scope']['request_budget']} requests -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
