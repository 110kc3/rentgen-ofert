"""Validate one generated regional dataset and publish a CI run summary.

Run after ``python -m scraper.main`` and before the data branch is pushed:

    python -m scripts.validate_data site/data/slaskie \
        --previous-meta /tmp/previous-meta-slaskie.json

Every JSON/JSON.GZ file is parsed. The dashboard manifest, index and detail
shards are checked as one atomic payload so a green scrape cannot publish a
missing, stale or mis-sharded file.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import pathlib
import sys

from scraper import payload


class DataValidationError(ValueError):
    pass


SOURCE_HEALTH_VALUES = frozenset({"healthy", "partial", "blocked", "unknown"})
UNAVAILABLE_SOURCE_STATUSES = frozenset({"blocked", "unknown"})


def _read_json(path: pathlib.Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise DataValidationError(f"invalid JSON: {path}: {exc}") from exc


def _read_gzip_json(path: pathlib.Path):
    try:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, UnicodeError, ValueError) as exc:
        raise DataValidationError(f"invalid gzip JSON: {path}: {exc}") from exc


def _require(condition, message):
    if not condition:
        raise DataValidationError(message)


def _number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _human_bytes(size: int) -> str:
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if value < 1024 or unit == "GiB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


def _source_transition(regression: dict) -> str:
    return (
        f"{regression['source']} "
        f"{regression['previous_status']}/{regression['previous_current']:,} -> "
        f"{regression['current_status']}/{regression['current_current']:,}"
    )


def validate_source_continuity(current_sources: dict, previous_meta=None,
                               *, allow_regression: bool = False) -> dict:
    """Reject categorical loss of a previously contributing source.

    A missing source is equivalent to an unknown source with zero current rows.
    Sources that were already unavailable, and first publications with no prior
    metadata, deliberately do not establish a positive baseline.
    """
    result = {
        "has_previous": previous_meta is not None,
        "checked": 0,
        "override": bool(allow_regression),
        "regressions": [],
    }
    if previous_meta is None:
        return result

    _require(isinstance(previous_meta, dict),
             "previous meta.json must contain an object")
    previous_coverage = previous_meta.get("coverage")
    _require(isinstance(previous_coverage, dict),
             "previous meta.coverage must be an object")
    previous_sources = previous_coverage.get("by_source")
    _require(isinstance(previous_sources, dict) and previous_sources,
             "previous meta.coverage.by_source must be a non-empty object")
    _require(isinstance(current_sources, dict),
             "current meta.coverage.by_source must be an object")

    regressions = []
    for name, previous in sorted(previous_sources.items()):
        _require(isinstance(previous, dict),
                 f"previous coverage source {name} must be an object")
        previous_status = previous.get("status")
        previous_current = previous.get("current")
        _require(previous_status in SOURCE_HEALTH_VALUES,
                 f"previous coverage source {name} has invalid health")
        _require(isinstance(previous_current, int)
                 and not isinstance(previous_current, bool)
                 and previous_current >= 0,
                 f"previous coverage source {name}.current must be a "
                 "non-negative integer")
        if (previous_current == 0
                or previous_status in UNAVAILABLE_SOURCE_STATUSES):
            continue

        result["checked"] += 1
        current = current_sources.get(name)
        if isinstance(current, dict):
            current_status = current.get("status", "unknown")
            current_current = current.get("current", 0)
        else:
            current_status = "unknown"
            current_current = 0
        _require(current_status in SOURCE_HEALTH_VALUES,
                 f"current coverage source {name} has invalid health")
        _require(isinstance(current_current, int)
                 and not isinstance(current_current, bool)
                 and current_current >= 0,
                 f"current coverage source {name}.current must be a "
                 "non-negative integer")
        if (current_status in UNAVAILABLE_SOURCE_STATUSES
                or current_current == 0):
            regressions.append({
                "source": name,
                "previous_status": previous_status,
                "previous_current": previous_current,
                "current_status": current_status,
                "current_current": current_current,
            })

    result["regressions"] = regressions
    if regressions and not allow_regression:
        transitions = "; ".join(
            _source_transition(item) for item in regressions
        )
        raise DataValidationError(
            "source continuity regression: " + transitions
            + "; refusing to replace a contributing source "
            "(use --allow-source-regression only for an intentional reset)"
        )
    return result


def validate_data_dir(data_dir, *, previous_meta=None,
                      allow_source_regression: bool = False) -> dict:
    root = pathlib.Path(data_dir)
    _require(root.is_dir(), f"regional data directory does not exist: {root}")

    json_paths = sorted(root.rglob("*.json"))
    gzip_paths = sorted(root.rglob("*.json.gz"))
    _require(json_paths, f"no JSON files found under {root}")
    parsed = {path: _read_json(path) for path in json_paths}
    for path in gzip_paths:
        _read_gzip_json(path)

    manifest_path = root / "manifest.json"
    index_path = root / "index.json"
    meta_path = root / "meta.json"
    archive_path = root / "archive.json"
    stats_path = root / "stats.json"
    history_path = root / "history.json.gz"
    for required in (manifest_path, index_path, meta_path,
                     archive_path, stats_path):
        _require(required in parsed, f"missing generated file: {required}")
    _require(history_path in gzip_paths,
             f"missing generated file: {history_path}")

    manifest = parsed[manifest_path]
    index = parsed[index_path]
    meta = parsed[meta_path]
    _require(isinstance(manifest, dict), "manifest.json must contain an object")
    _require(isinstance(index, list), "index.json must contain an array")
    _require(isinstance(meta, dict), "meta.json must contain an object")
    _require(isinstance(parsed[archive_path], list),
             "archive.json must contain an array")
    _require(isinstance(parsed[stats_path], dict),
             "stats.json must contain an object")

    shards = manifest.get("shards")
    count = manifest.get("count")
    version = manifest.get("v")
    _require(isinstance(shards, int) and shards > 0,
             "manifest.shards must be a positive integer")
    _require(isinstance(count, int) and count >= 0,
             "manifest.count must be a non-negative integer")
    _require(isinstance(version, str) and version,
             "manifest.v must be a non-empty string")
    _require(len(index) == count,
             f"manifest count {count} != index rows {len(index)}")

    expected_shards = {root / "d" / f"{i:02d}.json" for i in range(shards)}
    actual_shards = set((root / "d").glob("*.json")) if (root / "d").is_dir() else set()
    missing = sorted(str(path.relative_to(root)) for path in expected_shards - actual_shards)
    extra = sorted(str(path.relative_to(root)) for path in actual_shards - expected_shards)
    _require(not missing, f"missing detail shard(s): {', '.join(missing)}")
    _require(not extra, f"unexpected detail shard(s): {', '.join(extra)}")

    index_urls = set()
    for number, row in enumerate(index):
        _require(isinstance(row, dict), f"index row {number} is not an object")
        url = row.get("url")
        _require(isinstance(url, str) and url,
                 f"index row {number} has no URL")
        _require(url not in index_urls, f"duplicate index URL: {url}")
        index_urls.add(url)

    detail_urls = set()
    for shard_path in sorted(expected_shards):
        shard = parsed.get(shard_path)
        if shard is None:
            shard = _read_json(shard_path)
        _require(isinstance(shard, dict),
                 f"detail shard {shard_path.name} must contain an object")
        shard_number = int(shard_path.stem)
        for url, detail in shard.items():
            _require(url in index_urls,
                     f"detail URL is absent from index: {url}")
            _require(url not in detail_urls,
                     f"detail URL occurs in multiple shards: {url}")
            _require(payload.shard_of(url, shards) == shard_number,
                     f"detail URL is in the wrong shard: {url}")
            _require(isinstance(detail, dict),
                     f"detail for {url} must be an object")
            detail_urls.add(url)

    # Old regional branches remain readable during the serial rollout; new
    # publications include detail bytes in the version, not just the index.
    schema = manifest.get("schema", 1)
    _require(schema in (1, 2), f"unsupported manifest schema: {schema}")
    index_bytes = index_path.read_bytes()
    expected_version = (
        payload.content_version(index_bytes,
                                ((root / "d" / f"{i:02d}.json").read_bytes()
                                 for i in range(shards)))
        if schema == 2 else hashlib.sha1(index_bytes).hexdigest()[:10]
    )
    _require(version == expected_version,
             f"manifest version {version} != payload hash {expected_version}")

    _require(meta.get("count") == count,
             f"meta count {meta.get('count')} != manifest count {count}")
    _require(isinstance(meta.get("raw"), int) and meta["raw"] >= count,
             "meta.raw must be an integer at least as large as meta.count")
    by_type = meta.get("by_type")
    _require(isinstance(by_type, dict) and by_type,
             "meta.by_type must be a non-empty object")
    _require(all(isinstance(v, int) and not isinstance(v, bool) and v >= 0
                 for v in by_type.values()),
             "meta.by_type values must be non-negative integers")
    _require(sum(by_type.values()) == count,
             "meta.by_type does not add up to meta.count")
    coverage = meta.get("coverage")
    _require(isinstance(coverage, dict), "meta.coverage must be an object")
    _require(coverage.get("schema") == 2,
             "meta.coverage.schema must be 2")
    _require(coverage.get("status") in SOURCE_HEALTH_VALUES,
             "meta.coverage.status is invalid")
    _require(meta.get("health") == coverage.get("status"),
             "meta.health does not match coverage.status")
    sources = coverage.get("by_source")
    _require(isinstance(sources, dict) and sources,
             "meta.coverage.by_source must be a non-empty object")
    for name, source in sources.items():
        _require(isinstance(source, dict),
                 f"coverage source {name} must be an object")
        _require(source.get("status") in SOURCE_HEALTH_VALUES,
                 f"coverage source {name} has invalid health")
        for field in ("current", "served_unique"):
            value = source.get(field)
            _require(isinstance(value, int) and not isinstance(value, bool)
                     and value >= 0,
                     f"coverage source {name}.{field} must be a non-negative integer")

    runtime = meta.get("runtime")
    _require(isinstance(runtime, dict), "meta.runtime must be an object")
    _require(_number(runtime.get("seconds")) and runtime["seconds"] >= 0,
             "meta.runtime.seconds must be a non-negative number")
    phases = runtime.get("phases")
    _require(isinstance(phases, dict) and phases,
             "meta.runtime.phases must be a non-empty object")
    _require(all(_number(value) and value >= 0 for value in phases.values()),
             "meta.runtime phase values must be non-negative numbers")
    _require(phases.get("total") == runtime["seconds"],
             "meta.runtime.phases.total must match meta.runtime.seconds")

    photos = meta.get("photos")
    _require(isinstance(photos, dict), "meta.photos must be an object")
    _require(photos.get("schema") == 3, "meta.photos.schema must be 3")
    _require(isinstance(photos.get("enabled"), bool),
             "meta.photos.enabled must be a boolean")
    _require(isinstance(photos.get("listings"), int)
             and not isinstance(photos["listings"], bool)
             and photos["listings"] >= 0,
             "meta.photos.listings must be a non-negative integer")
    _require(isinstance(photos.get("heuristic_fallback_enabled"), bool),
             "meta.photos.heuristic_fallback_enabled must be a boolean")
    _require(photos["heuristic_fallback_enabled"] == (not photos["enabled"]),
             "meta.photos heuristic fallback must be disabled in photo mode")
    if photos["enabled"]:
        count_fields = (
            "critical", "history_only", "cache_hits", "fetched",
            "with_photos", "identified", "deferred",
            "critical_deferred", "history_deferred",
            "cover_cache_hits", "gallery_cache_hits",
            "cover_fetched", "gallery_fetched",
            "critical_with_photos", "critical_without_photos",
            "unresolved_size_groups", "unresolved_size_listings",
        )
        for field in count_fields:
            value = photos.get(field)
            _require(isinstance(value, int) and not isinstance(value, bool)
                     and value >= 0,
                     f"meta.photos.{field} must be a non-negative integer")
        _require(
            photos["critical"] + photos["history_only"]
            + photos["identified"] == photos["listings"],
            "meta.photos queue counts do not add up to listings",
        )
        _require(
            photos["cache_hits"] + photos["fetched"]
            + photos["identified"] + photos["deferred"]
            == photos["listings"],
            "meta.photos outcomes do not add up to listings",
        )
        _require(
            photos["cover_cache_hits"] + photos["gallery_cache_hits"]
            == photos["cache_hits"],
            "meta.photos cache scopes do not add up to cache_hits",
        )
        _require(
            photos["cover_fetched"] + photos["gallery_fetched"]
            == photos["fetched"],
            "meta.photos fetch scopes do not add up to fetched",
        )
        _require(photos["critical_deferred"] <= photos["critical"],
                 "meta.photos.critical_deferred exceeds critical")
        _require(
            photos["critical_with_photos"]
            + photos["critical_without_photos"]
            + photos["critical_deferred"] == photos["critical"],
            "meta.photos critical outcomes do not add up",
        )
        _require(photos["critical_with_photos"] <= photos["with_photos"],
                 "meta.photos.critical_with_photos exceeds with_photos")
        _require(
            photos["unresolved_size_listings"]
            <= photos["critical_without_photos"]
            + photos["critical_deferred"],
            "meta.photos unresolved listings exceed unresolved critical rows",
        )
        _require(
            (photos["unresolved_size_groups"] == 0
             and photos["unresolved_size_listings"] == 0)
            or (photos["unresolved_size_groups"] > 0
                and photos["unresolved_size_listings"]
                >= 2 * photos["unresolved_size_groups"]),
            "meta.photos unresolved size-group counts are inconsistent",
        )
        _require(
            photos["critical_deferred"] + photos["history_deferred"]
            == photos["deferred"],
            "meta.photos deferred counts do not add up",
        )
        _require(photos["with_photos"]
                 <= photos["cache_hits"] + photos["fetched"],
                 "meta.photos.with_photos exceeds attempted/cache outcomes")
        backlog = photos.get("backlog")
        _require(isinstance(backlog, dict),
                 "meta.photos.backlog must be an object")
        _require(isinstance(backlog.get("count"), int)
                 and not isinstance(backlog["count"], bool)
                 and 0 <= backlog["count"] <= photos["deferred"],
                 "meta.photos.backlog.count is invalid")
        _require(isinstance(backlog.get("age_days"), int)
                 and not isinstance(backlog["age_days"], bool)
                 and backlog["age_days"] >= 0,
                 "meta.photos.backlog.age_days must be a non-negative integer")
        oldest = backlog.get("oldest")
        _require((backlog["count"] == 0 and oldest is None)
                 or (backlog["count"] > 0
                     and isinstance(oldest, str) and oldest),
                 "meta.photos.backlog.oldest does not match its count")

    all_files = [path for path in root.rglob("*") if path.is_file()]
    generated_bytes = sum(path.stat().st_size for path in all_files)
    published_bytes = sum(path.stat().st_size for path in all_files
                          if path.name != "history.json.gz")
    summary = {
        "region": root.name,
        "count": count,
        "raw": int(meta.get("raw") or 0),
        "health": meta.get("health"),
        "json_files": len(json_paths) + len(gzip_paths),
        "shards": shards,
        "detail_records": len(detail_urls),
        "generated_bytes": generated_bytes,
        "published_bytes": published_bytes,
        "runtime": runtime,
        "photos": photos,
        "sources": sources,
    }
    summary["continuity"] = validate_source_continuity(
        sources,
        previous_meta,
        allow_regression=allow_source_regression,
    )
    return summary


def github_summary(summary: dict) -> str:
    lines = [
        f"## Dataset: {summary['region']}",
        "",
        (f"**{summary['count']:,} properties** from {summary['raw']:,} raw rows · "
         f"health **{summary['health']}** · "
         f"{_human_bytes(summary['published_bytes'])} published "
         f"({_human_bytes(summary['generated_bytes'])} including pipeline history) · "
         f"{summary['json_files']} JSON files validated"),
        "",
        "| Source | Health | Current | Served | Coverage |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, source in sorted(summary["sources"].items()):
        pct = f"{source['pct']:.1f}%" if source.get("pct") is not None else "—"
        lines.append(
            f"| {name} | {source.get('status', 'unknown')} | "
            f"{int(source.get('current') or 0):,} | "
            f"{int(source.get('served_unique') or 0):,} | {pct} |")
    continuity = summary.get("continuity")
    if continuity:
        regressions = continuity["regressions"]
        if not continuity["has_previous"]:
            continuity_line = "first publication; no prior baseline"
        elif regressions:
            transitions = "; ".join(
                _source_transition(item) for item in regressions
            )
            continuity_line = f"operator override accepted ({transitions})"
        else:
            continuity_line = (
                f"{continuity['checked']} prior contributing source(s) retained"
            )
            if continuity["override"]:
                continuity_line += "; operator override enabled"
        lines.extend(["", f"**Source continuity:** {continuity_line}."])
    lines.extend(["", "| Phase | Time |", "|---|---:|"])
    for name, seconds in summary["runtime"]["phases"].items():
        lines.append(f"| {name} | {float(seconds):.1f}s |")
    photos = summary["photos"]
    if photos["enabled"]:
        backlog = photos["backlog"]
        lines.extend([
            "",
            (f"**Photo queue:** {photos['critical']:,} correctness-critical · "
             f"{photos['critical_with_photos']:,} critical with photos · "
             f"{photos['critical_without_photos']:,} critical without photos · "
             f"{photos['unresolved_size_groups']:,} unresolved size groups "
             f"({photos['unresolved_size_listings']:,} listings; kept separate) · "
             f"{photos['history_only']:,} history-only · "
             f"{photos['cache_hits']:,} cache hits "
             f"({photos['cover_cache_hits']:,} cover) · "
             f"{photos['fetched']:,} fetched "
             f"({photos['cover_fetched']:,} cover) · "
             f"{photos['deferred']:,} total deferred "
             f"({photos['critical_deferred']:,} critical) · "
             f"backlog {backlog['count']:,}, oldest "
             f"{backlog['oldest'] or '—'}"),
        ])
    lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(
        description="Validate generated regional data before publication.")
    parser.add_argument("data_dir", help="site/data/<region> directory")
    parser.add_argument(
        "--previous-meta",
        help="prior publication's meta.json for source-continuity checks",
    )
    parser.add_argument(
        "--allow-source-regression",
        action="store_true",
        help="explicitly allow a contributing source to become unavailable",
    )
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    if args.allow_source_regression:
        print(
            "::warning::Source-continuity override enabled; an unavailable "
            "previously contributing source may be published.",
            file=sys.stderr,
        )
    try:
        previous_meta = (_read_json(pathlib.Path(args.previous_meta))
                         if args.previous_meta else None)
        summary = validate_data_dir(
            args.data_dir,
            previous_meta=previous_meta,
            allow_source_regression=args.allow_source_regression,
        )
    except DataValidationError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1

    regressions = summary["continuity"]["regressions"]
    if regressions:
        transitions = "; ".join(
            _source_transition(item) for item in regressions
        )
        print(f"::warning::Source-continuity override accepted: {transitions}",
              file=sys.stderr)

    line = (f"Validated {summary['region']}: {summary['count']:,} properties, "
            f"health {summary['health']}, {summary['json_files']} JSON files, "
            f"{_human_bytes(summary['published_bytes'])} published")
    print(line)
    destination = os.environ.get("GITHUB_STEP_SUMMARY")
    if destination:
        with open(destination, "a", encoding="utf-8") as handle:
            handle.write(github_summary(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
