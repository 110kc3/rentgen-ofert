import datetime as dt
import json
import pathlib

import pytest

from scripts import check_freshness as freshness

NOW = dt.datetime(2026, 11, 18, 12, 0, tzinfo=dt.timezone.utc)
WORKFLOW = pathlib.Path(__file__).resolve().parent.parent / ".github/workflows/freshness.yml"


def region(slug, cadence, enabled=True):
    return {"slug": slug, "cadence": cadence, "enabled": enabled}


def catalog_of(*entries):
    return {"default": entries[0]["slug"], "regions": list(entries)}


def published(hours_ago):
    return {"updated": (NOW - dt.timedelta(hours=hours_ago)).isoformat().replace("+00:00", "Z")}


def reader(metas):
    def read(slug):
        value = metas[slug]
        if isinstance(value, Exception):
            raise value
        return value
    return read


def test_fresh_regions_pass(capsys):
    document = catalog_of(region("slaskie", "twice_daily"), region("opolskie", "every_72h"))
    metas = {"slaskie": published(13), "opolskie": published(100)}
    assert freshness.main(document, NOW, reader(metas)) == 0
    assert "slaskie: fresh" in capsys.readouterr().out


@pytest.mark.parametrize("cadence, hours", [("twice_daily", 37), ("every_72h", 121),
                                            ("daily", 49), ("weekly", 24 * 9 + 1)])
def test_overdue_publication_fails(cadence, hours, capsys):
    document = catalog_of(region("slaskie", cadence))
    assert freshness.main(document, NOW, reader({"slaskie": published(hours)})) == 1
    assert "slaskie: STALE" in capsys.readouterr().out


def test_november_freeze_is_reported_stale():
    document = catalog_of(region("slaskie", "twice_daily"), region("opolskie", "every_72h"))
    metas = {"slaskie": {"updated": "2026-11-04T16:48:07Z"},
             "opolskie": {"updated": "2026-11-04T09:30:04Z"}}
    report = freshness.freshness_report(document, NOW, reader(metas))
    assert all(report.values())


@pytest.mark.parametrize("meta", [OSError("HTTP 404"), {}, {"updated": "not a date"},
                                  {"updated": "2026-11-18T10:00:00"}, None])
def test_unreadable_metadata_fails(meta):
    document = catalog_of(region("slaskie", "twice_daily"))
    assert freshness.main(document, NOW, reader({"slaskie": meta})) == 1


def test_disabled_and_manual_regions_are_ignored():
    document = catalog_of(region("slaskie", "twice_daily"),
                          region("opolskie", "every_72h", enabled=False),
                          region("lubuskie", "manual"))
    report = freshness.freshness_report(document, NOW, reader({"slaskie": published(1)}))
    assert list(report) == ["slaskie"]


def test_summary_is_written(tmp_path, monkeypatch):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    document = catalog_of(region("slaskie", "twice_daily"))
    freshness.main(document, NOW, reader({"slaskie": published(40)}))
    assert "STALE" in summary.read_text()


def test_production_catalog_monitors_live_cadences():
    monitored = {entry["slug"] for entry in freshness.monitored_regions(
        json.loads((WORKFLOW.parents[2] / "site/regions.json").read_text()))}
    assert {"slaskie", "opolskie"} <= monitored


def test_workflow_runs_the_check_read_only():
    text = WORKFLOW.read_text()
    assert "python3 -m scripts.check_freshness" in text
    assert "contents: read" in text
    assert "write" not in text
