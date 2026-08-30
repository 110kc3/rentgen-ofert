"""Generated regional-data gate (offline)."""
import gzip
import json

import pytest

from scraper import payload
from scripts import validate_data


def _dataset(tmp_path):
    listings = [
        {
            "title": "Flat", "type": "flat", "area": 50,
            "url": "https://example.test/flat/1", "source": "otodom",
            "offers": [{"source": "otodom", "url": "https://example.test/flat/1"}],
        },
        {
            "title": "House", "type": "house", "area": 120,
            "url": "https://example.test/house/2", "source": "gratka",
            "timeline": [{"date": "2026-08-24", "kind": "listed"}],
        },
    ]
    payload.build(listings, tmp_path, shards=4, log=lambda *a: None)
    coverage = {
        "schema": 2,
        "status": "partial",
        "by_source": {
            "otodom": {
                "status": "partial", "current": 1, "served_unique": 1,
                "pct": 72.7,
            },
            "gratka": {
                "status": "healthy", "current": 1, "served_unique": 1,
                "pct": 100.0,
            },
        },
        "issues": [], "truncated": [],
    }
    (tmp_path / "meta.json").write_text(json.dumps({
        "updated": "2026-08-24T10:00:00+00:00",
        "count": 2, "raw": 2, "by_type": {"flat": 1, "house": 1},
        "health": "partial", "coverage": coverage,
        "runtime": {
            "seconds": 12.5,
            "phases": {"scrape_otodom": 3.0, "write": 0.5, "total": 12.5},
        },
        "photos": {
            "schema": 3, "enabled": True, "listings": 2, "critical": 1,
            "heuristic_fallback_enabled": False,
            "history_only": 1, "cache_hits": 1, "fetched": 0,
            "cover_cache_hits": 1, "gallery_cache_hits": 0,
            "cover_fetched": 0, "gallery_fetched": 0,
            "with_photos": 1, "identified": 0, "deferred": 1,
            "critical_deferred": 0, "history_deferred": 1,
            "critical_with_photos": 1, "critical_without_photos": 0,
            "unresolved_size_groups": 0, "unresolved_size_listings": 0,
            "backlog": {"count": 1, "oldest": "2026-08-24", "age_days": 0},
        },
    }), encoding="utf-8")
    (tmp_path / "archive.json").write_text("[]", encoding="utf-8")
    (tmp_path / "stats.json").write_text("{}", encoding="utf-8")
    with gzip.open(tmp_path / "history.json.gz", "wt", encoding="utf-8") as handle:
        json.dump([], handle)
    return tmp_path


def _meta(root):
    return json.loads((root / "meta.json").read_text(encoding="utf-8"))


def test_generated_dataset_validator_checks_every_payload_part(tmp_path):
    root = _dataset(tmp_path)
    summary = validate_data.validate_data_dir(root)
    assert summary["count"] == 2 and summary["shards"] == 4
    assert summary["json_files"] == 10  # 5 top-level JSON + 4 shards + gzip
    assert summary["detail_records"] == 2
    assert summary["generated_bytes"] > summary["published_bytes"]
    markdown = validate_data.github_summary(summary)
    assert "Dataset:" in markdown and "otodom" in markdown
    assert "scrape_otodom" in markdown and "published" in markdown
    assert "Photo queue" in markdown and "1 total deferred" in markdown
    assert "1 critical with photos" in markdown
    assert "0 critical without photos" in markdown
    assert "0 unresolved size groups" in markdown


def test_generated_dataset_validator_rejects_count_mismatch(tmp_path):
    root = _dataset(tmp_path)
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["count"] = 99
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(validate_data.DataValidationError, match="manifest count"):
        validate_data.validate_data_dir(root)


def test_generated_dataset_validator_rejects_a_missharded_detail(tmp_path):
    root = _dataset(tmp_path)
    url = "https://example.test/flat/1"
    source_number = payload.shard_of(url, 4)
    target_number = (source_number + 1) % 4
    source_path = root / "d" / f"{source_number:02d}.json"
    target_path = root / "d" / f"{target_number:02d}.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    target = json.loads(target_path.read_text(encoding="utf-8"))
    target[url] = source.pop(url)
    source_path.write_text(json.dumps(source), encoding="utf-8")
    target_path.write_text(json.dumps(target), encoding="utf-8")

    with pytest.raises(validate_data.DataValidationError, match="wrong shard"):
        validate_data.validate_data_dir(root)


def test_generated_dataset_validator_requires_pipeline_outputs(tmp_path):
    root = _dataset(tmp_path)
    (root / "history.json.gz").unlink()

    with pytest.raises(validate_data.DataValidationError,
                       match="missing generated file.*history.json.gz"):
        validate_data.validate_data_dir(root)


def test_generated_dataset_validator_rejects_inconsistent_photo_metrics(tmp_path):
    root = _dataset(tmp_path)
    meta_path = root / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["photos"]["critical_deferred"] = 2
    meta_path.write_text(json.dumps(meta), encoding="utf-8")

    with pytest.raises(validate_data.DataValidationError,
                       match="critical_deferred exceeds critical"):
        validate_data.validate_data_dir(root)


def test_generated_dataset_validator_rejects_inconsistent_photo_scopes(tmp_path):
    root = _dataset(tmp_path)
    meta_path = root / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["photos"]["gallery_cache_hits"] = 1
    meta_path.write_text(json.dumps(meta), encoding="utf-8")

    with pytest.raises(validate_data.DataValidationError,
                       match="cache scopes do not add up"):
        validate_data.validate_data_dir(root)


def test_generated_dataset_validator_rejects_photo_mode_with_heuristic_fallback(
        tmp_path):
    root = _dataset(tmp_path)
    meta_path = root / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["photos"]["heuristic_fallback_enabled"] = True
    meta_path.write_text(json.dumps(meta), encoding="utf-8")

    with pytest.raises(validate_data.DataValidationError,
                       match="heuristic fallback must be disabled"):
        validate_data.validate_data_dir(root)


def test_generated_dataset_validator_rejects_impossible_unresolved_group_counts(
        tmp_path):
    root = _dataset(tmp_path)
    meta_path = root / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["photos"]["critical_with_photos"] = 0
    meta["photos"]["critical_without_photos"] = 1
    meta["photos"]["unresolved_size_groups"] = 1
    meta["photos"]["unresolved_size_listings"] = 1
    meta_path.write_text(json.dumps(meta), encoding="utf-8")

    with pytest.raises(validate_data.DataValidationError,
                       match="unresolved size-group counts are inconsistent"):
        validate_data.validate_data_dir(root)


def test_source_continuity_allows_a_first_publication(tmp_path):
    summary = validate_data.validate_data_dir(_dataset(tmp_path))

    assert summary["continuity"] == {
        "has_previous": False,
        "checked": 0,
        "override": False,
        "regressions": [],
    }


def test_source_continuity_allows_a_persistently_blocked_source(tmp_path):
    root = _dataset(tmp_path)
    previous = _meta(root)
    blocked = {"status": "blocked", "current": 0, "served_unique": 0}
    previous["coverage"]["by_source"]["olx"] = blocked
    current_path = root / "meta.json"
    current = _meta(root)
    current["coverage"]["by_source"]["olx"] = blocked
    current_path.write_text(json.dumps(current), encoding="utf-8")

    summary = validate_data.validate_data_dir(root, previous_meta=previous)

    assert summary["continuity"]["checked"] == 2
    assert summary["continuity"]["regressions"] == []


def test_source_continuity_rejects_a_contributing_source_outage(tmp_path):
    root = _dataset(tmp_path)
    previous = _meta(root)
    previous_otodom = previous["coverage"]["by_source"]["otodom"]
    previous_otodom.update(status="partial", current=15_949,
                            served_unique=15_949)
    current_path = root / "meta.json"
    current = _meta(root)
    current_otodom = current["coverage"]["by_source"]["otodom"]
    current_otodom.update(status="blocked", current=0, served_unique=0)
    current_path.write_text(json.dumps(current), encoding="utf-8")

    with pytest.raises(
            validate_data.DataValidationError,
            match=r"source continuity regression: otodom partial/15,949 -> blocked/0"):
        validate_data.validate_data_dir(root, previous_meta=previous)


def test_source_continuity_treats_a_removed_source_as_unknown_zero(tmp_path):
    root = _dataset(tmp_path)
    previous = _meta(root)
    current_path = root / "meta.json"
    current = _meta(root)
    del current["coverage"]["by_source"]["otodom"]
    current_path.write_text(json.dumps(current), encoding="utf-8")

    with pytest.raises(validate_data.DataValidationError,
                       match=r"otodom partial/1 -> unknown/0"):
        validate_data.validate_data_dir(root, previous_meta=previous)


@pytest.mark.parametrize(("status", "current_count"), [
    ("unknown", 1),
    ("healthy", 0),
])
def test_source_continuity_rejects_each_unavailable_condition(
        tmp_path, status, current_count):
    root = _dataset(tmp_path)
    previous = _meta(root)
    current = _meta(root)
    current["coverage"]["by_source"]["otodom"].update(
        status=status,
        current=current_count,
        served_unique=current_count,
    )
    (root / "meta.json").write_text(json.dumps(current), encoding="utf-8")

    with pytest.raises(validate_data.DataValidationError,
                       match="source continuity regression: otodom"):
        validate_data.validate_data_dir(root, previous_meta=previous)


def test_source_continuity_allows_positive_drift_and_blocked_recovery(tmp_path):
    root = _dataset(tmp_path)
    previous = _meta(root)
    previous_otodom = previous["coverage"]["by_source"]["otodom"]
    previous_otodom.update(status="blocked", current=0, served_unique=0)
    previous_gratka = previous["coverage"]["by_source"]["gratka"]
    previous_gratka.update(current=12_000, served_unique=12_000)

    summary = validate_data.validate_data_dir(root, previous_meta=previous)

    assert summary["continuity"]["checked"] == 1
    assert summary["continuity"]["regressions"] == []


def test_source_continuity_override_is_explicit_and_reported(tmp_path, capsys):
    root = _dataset(tmp_path / "current")
    previous = _meta(root)
    previous["coverage"]["by_source"]["otodom"].update(
        current=15_949, served_unique=15_949)
    current = _meta(root)
    current["coverage"]["by_source"]["otodom"].update(
        status="blocked", current=0, served_unique=0)
    (root / "meta.json").write_text(json.dumps(current), encoding="utf-8")
    previous_path = tmp_path / "previous-meta.json"
    previous_path.write_text(json.dumps(previous), encoding="utf-8")

    result = validate_data.main([
        str(root), "--previous-meta", str(previous_path),
        "--allow-source-regression",
    ])

    assert result == 0
    assert "override enabled" in capsys.readouterr().err


def test_source_continuity_rejects_malformed_previous_metadata(tmp_path):
    root = _dataset(tmp_path)

    with pytest.raises(validate_data.DataValidationError,
                       match="previous meta.coverage must be an object"):
        validate_data.validate_data_dir(root, previous_meta={})
