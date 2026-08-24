"""Validate one generated regional dataset and publish a CI run summary.

Run after ``python -m scraper.main`` and before the data branch is pushed:

    python -m scripts.validate_data site/data/slaskie

Every JSON/JSON.GZ file is parsed. The dashboard manifest, index and detail
shards are checked as one atomic payload so a green scrape cannot publish a
missing, stale or mis-sharded file.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import pathlib
import sys

from scraper import payload


class DataValidationError(ValueError):
    pass


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


def validate_data_dir(data_dir) -> dict:
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

    index_bytes = index_path.read_bytes()
    expected_version = hashlib.sha1(index_bytes).hexdigest()[:10]
    _require(version == expected_version,
             f"manifest version {version} != index hash {expected_version}")

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
    health_values = {"healthy", "partial", "blocked", "unknown"}
    _require(coverage.get("status") in health_values,
             "meta.coverage.status is invalid")
    _require(meta.get("health") == coverage.get("status"),
             "meta.health does not match coverage.status")
    sources = coverage.get("by_source")
    _require(isinstance(sources, dict) and sources,
             "meta.coverage.by_source must be a non-empty object")
    for name, source in sources.items():
        _require(isinstance(source, dict),
                 f"coverage source {name} must be an object")
        _require(source.get("status") in health_values,
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

    all_files = [path for path in root.rglob("*") if path.is_file()]
    generated_bytes = sum(path.stat().st_size for path in all_files)
    published_bytes = sum(path.stat().st_size for path in all_files
                          if path.name != "history.json.gz")
    return {
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
        "sources": sources,
    }


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
    lines.extend(["", "| Phase | Time |", "|---|---:|"])
    for name, seconds in summary["runtime"]["phases"].items():
        lines.append(f"| {name} | {float(seconds):.1f}s |")
    lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        print("usage: python -m scripts.validate_data site/data/<region>",
              file=sys.stderr)
        return 2
    try:
        summary = validate_data_dir(argv[0])
    except DataValidationError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1

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
