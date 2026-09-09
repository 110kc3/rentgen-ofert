"""Cadence boundaries, fail-closed metadata and manual/scheduled isolation."""
import copy
import datetime as dt
import json
import urllib.error

import pytest

from scraper.regions import catalog, RegionCatalogError
from scripts import schedule_region as schedule

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 9, 9, 12, tzinfo=UTC)


def decide(age=72, *, document=None, **kwargs):
    previous = kwargs.pop("previous", lambda _: {
        "updated": (NOW - dt.timedelta(hours=age)).isoformat()})
    return schedule.decide(
        kwargs.pop("event", "schedule"), kwargs.pop("cron", schedule.OPOLSKIE_CRON),
        kwargs.pop("requested", ""), document or catalog(), NOW, previous, kwargs.pop("attempts", lambda _: []),
    )


@pytest.mark.parametrize("age,run", [(0, False), (71.999, False), (72, True), (96, True)])
def test_due_only_after_72_hours_from_success(age, run):
    slug, actual, reason = decide(age)
    assert slug == "opolskie"
    assert actual is run
    assert reason


def test_month_boundary_and_non_utc_timestamp():
    result = schedule.decide("schedule", schedule.OPOLSKIE_CRON, "", catalog(),
                             dt.datetime(2026, 3, 2, 22, tzinfo=UTC),
                             lambda _: {"updated": "2026-02-28T00:00:00+02:00"})
    assert result[1] is True


@pytest.mark.parametrize("value", [None, [], {}, {"updated": 3},
                                   {"updated": "bad"}, {"updated": "2026-09-01"},
                                   {"updated": "2026-09-10T00:00:00Z"}])
def test_missing_malformed_or_future_metadata_fails_closed(value):
    with pytest.raises(ValueError):
        decide(previous=lambda _: value)


def test_failed_read_is_not_permission_to_scrape():
    def failed(_):
        raise urllib.error.HTTPError("https://api.github.com", 404, "missing", {}, None)
    with pytest.raises(urllib.error.HTTPError):
        decide(previous=failed)


def no_read(_):
    pytest.fail("this event must not read pilot metadata")


@pytest.mark.parametrize("change", [{"enabled": False}, {"cadence": "manual"}])
def test_catalog_can_disable_scheduling_without_portal_or_metadata_work(change):
    document = copy.deepcopy(catalog())
    next(r for r in document["regions"] if r["slug"] == "opolskie").update(change)
    assert decide(document=document, previous=no_read)[1] is False


def test_slaskie_schedule_and_code_push_keep_their_region():
    assert decide(cron=schedule.SLASKIE_CRON, previous=no_read)[:2] == ("slaskie", True)
    assert decide(event="push", requested="opolskie", previous=no_read)[:2] == ("slaskie", True)


def test_manual_dispatch_bypasses_time_but_not_enabled_validation():
    assert decide(event="workflow_dispatch", requested="opolskie", previous=no_read)[:2] == ("opolskie", True)
    assert decide(event="workflow_dispatch", previous=no_read)[:2] == ("slaskie", True)
    for slug in ("malopolskie", "../opolskie", "unknown"):
        with pytest.raises(RegionCatalogError):
            decide(event="workflow_dispatch", requested=slug, previous=no_read)


def test_unrecognized_trigger_fails_closed():
    with pytest.raises(ValueError):
        decide(cron="0 0 */3 * *", previous=no_read)
    with pytest.raises(ValueError):
        decide(event="pull_request", previous=no_read)


def test_queued_check_reloads_success_instead_of_reusing_an_old_decision():
    assert decide(80)[1] is True
    assert decide(0)[1] is False


def test_cli_exports_only_a_validated_region_and_records_skip(monkeypatch, tmp_path):
    for key, value in {"GITHUB_EVENT_NAME": "schedule", "SCHEDULE": schedule.OPOLSKIE_CRON,
                       "GITHUB_REPOSITORY": "owner/repo", "REQUESTED_REGION": "../bad"}.items():
        monkeypatch.setenv(key, value)
    for key in ("GITHUB_OUTPUT", "GITHUB_ENV", "GITHUB_STEP_SUMMARY"):
        monkeypatch.setenv(key, str(tmp_path / key))
    monkeypatch.setattr(schedule, "read_previous", lambda *args: {
        "updated": (dt.datetime.now(UTC) - dt.timedelta(seconds=1)).isoformat()})
    schedule.main()
    assert (tmp_path / "GITHUB_OUTPUT").read_text() == "run=false\n"
    assert (tmp_path / "GITHUB_ENV").read_text() == "REGION=opolskie\nDATA_BRANCH=data-opolskie\n"
    assert "skip" in (tmp_path / "GITHUB_STEP_SUMMARY").read_text()


def test_metadata_reader_uses_data_branch_not_pages(monkeypatch):
    import io
    def response(request, timeout):
        assert request.full_url == (
            "https://api.github.com/repos/owner/repo/contents/"
            "site/data/opolskie/meta.json?ref=data-opolskie")
        assert timeout == 30
        return io.BytesIO(json.dumps({"updated": NOW.isoformat()}).encode())
    monkeypatch.setattr(schedule.urllib.request, "urlopen", response)
    assert schedule.read_previous("owner/repo", "opolskie")["updated"] == NOW.isoformat()


@pytest.mark.parametrize("age,run", [(0, False), (71.999, False), (72, True), (96, True)])
def test_failed_attempt_still_gets_a_72_hour_cooldown(age, run):
    assert decide(100, attempts=lambda _: [(NOW - dt.timedelta(hours=age)).isoformat()])[1] is run


def test_attempt_read_failure_or_bad_timestamp_prevents_retries():
    with pytest.raises(ValueError):
        decide(100, attempts=lambda _: ["not a timestamp"])
    with pytest.raises(ValueError):
        decide(100, attempts=lambda _: [(NOW + dt.timedelta(hours=1)).isoformat()])
    with pytest.raises(urllib.error.HTTPError):
        decide(100, attempts=lambda _: (_ for _ in ()).throw(
            urllib.error.HTTPError("api", 500, "failed", {}, None)))


def test_attempt_reader_does_not_assume_api_order_or_ignore_incomplete_pages(monkeypatch):
    monkeypatch.setattr(schedule, "read_api", lambda *args: {
        "total_count": 2, "artifacts": [{"created_at": "2026-09-05T00:00:00Z"},
                                         {"created_at": "2026-09-08T00:00:00Z"}]})
    assert decide(100, attempts=lambda r: schedule.read_last_attempt("owner/repo", r))[1] is False
    monkeypatch.setattr(schedule, "read_api", lambda *args: {"total_count": 101, "artifacts": []})
    with pytest.raises(ValueError):
        schedule.read_last_attempt("owner/repo", "opolskie")
