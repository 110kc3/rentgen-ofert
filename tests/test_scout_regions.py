"""P3's nationwide scout stays bounded, read-only and fixture-testable."""
import datetime as dt
import json
import pathlib

import requests

from scraper import regions
from scripts import scout_regions


ROOT = pathlib.Path(__file__).parents[1]


def _otodom_html(total=101, items=1):
    payload = {
        "props": {"pageProps": {"data": {"searchAds": {
            "items": [{"id": number} for number in range(items)],
            "pagination": {"totalItems": total, "totalPages": 2},
        }}}},
    }
    return '<script id="__NEXT_DATA__">' + json.dumps(payload) + "</script>"


def _olx_html(visible=202, servable=100, items=1):
    state = {"listing": {"listing": {
        "ads": [{"id": number} for number in range(items)],
        "visibleElements": visible,
        "totalElements": servable,
        "totalPages": 3,
    }}}
    # OLX JSON-encodes the state and then embeds that JSON string in JS.
    encoded = json.dumps(json.dumps(state, separators=(",", ":")))
    return f"<script>window.__PRERENDERED_STATE__ = {encoded};</script>"


def _cards_html(total=303, minimum=False):
    qualifier = "ponad " if minimum else ""
    return f"""
      <meta name="description" content="{qualifier}{total} ogłoszeń">
      <article data-cy="card"><a data-cy="propertyUrl" href="/offer/123"></a></article>
    """


class Response:
    def __init__(self, status_code, text, url):
        self.status_code = status_code
        self.text = text
        self.url = url


class Session:
    def __init__(self, olx_status=200):
        self.calls = []
        self.olx_status = olx_status

    def get(self, url, headers=None, timeout=None):
        self.calls.append({"url": url, "headers": headers, "timeout": timeout})
        if "otodom.pl" in url:
            return Response(200, _otodom_html(), url)
        if "olx.pl" in url:
            return Response(self.olx_status, _olx_html(), url)
        if "gratka.pl" in url:
            return Response(200, _cards_html(), url)
        if "morizon.pl" in url:
            return Response(200, _cards_html(404, minimum=True), url)
        raise AssertionError(f"unexpected scout URL: {url}")


def test_search_urls_use_explicit_slug_and_only_page_one():
    slug = "portal-specific-slug"
    urls = {
        (source, typ): scout_regions.search_url(source, typ, slug)
        for source in regions.PORTALS for typ in scout_regions.TYPES
    }

    assert all(f"/{slug}" in url for url in urls.values())
    assert urls["otodom", "house"].endswith(
        f"/{slug}?page=1&limit=72")
    assert "/sprzedaz/dom/" in urls["otodom", "house"]
    assert "/sprzedaz/mieszkanie/" in urls["otodom", "flat"]
    assert urls["olx", "flat"].endswith(f"/{slug}/?page=1")
    assert "page=2" not in " ".join(urls.values())


def test_each_portal_parser_keeps_only_aggregate_evidence():
    assert scout_regions.parse_page("otodom", "house", _otodom_html()) == {
        "declared_inventory": 101,
        "declared_is_minimum": False,
        "page_items": 1,
        "servable_inventory": None,
    }
    assert scout_regions.parse_page("olx", "flat", _olx_html()) == {
        "declared_inventory": 202,
        "declared_is_minimum": False,
        "page_items": 1,
        "servable_inventory": 100,
    }
    assert scout_regions.parse_page("gratka", "house", _cards_html()) == {
        "declared_inventory": 303,
        "declared_is_minimum": False,
        "page_items": 1,
        "servable_inventory": None,
    }
    assert scout_regions.parse_page(
        "morizon", "flat", _cards_html(404, minimum=True)
    )["declared_is_minimum"] is True


def test_successful_scout_has_all_128_targets_and_exact_request_budget():
    session = Session()
    report = scout_regions.scout(
        regions.load_catalog(), session=session, delay=0, sleep=lambda _: None,
        log=lambda _: None,
        now=dt.datetime(2026, 8, 31, 9, 0, tzinfo=dt.timezone.utc),
        clock=lambda: 0)

    assert report["schema"] == 1
    assert report["generated_at"] == "2026-08-31T09:00:00Z"
    assert report["scope"] == {
        "regions": 16,
        "sources": list(regions.PORTALS),
        "types": ["house", "flat"],
        "pages_per_target": 1,
        "target_probes": 128,
        "request_budget": 128,
        "requests_made": 128,
        "retry_budget": 0,
        "runtime_budget_seconds": 2400,
        "elapsed_seconds": 0,
        "runtime_budget_exhausted": False,
        "excluded_sources": scout_regions.EXCLUDED_SOURCES,
    }
    assert len(session.calls) == len(report["probes"]) == 128
    assert {row["region"] for row in report["probes"]} == {
        entry["slug"] for entry in regions.load_catalog()["regions"]}
    assert report["summary"]["status_counts"] == {"ok": 128}
    assert all(call["timeout"] == 20 for call in session.calls)
    assert all(row["page_items"] == 1 for row in report["probes"])


def test_one_refusal_stops_that_source_without_dropping_target_rows():
    session = Session(olx_status=403)
    report = scout_regions.scout(
        regions.load_catalog(), session=session, delay=0, sleep=lambda _: None,
        log=lambda _: None)

    # Otodom, Gratka and Morizon each use 32 requests. OLX uses one, then its
    # remaining 31 targets become explicit skips rather than repeated blocks.
    assert len(session.calls) == report["scope"]["requests_made"] == 97
    assert len(report["probes"]) == 128
    assert report["summary"]["status_counts"] == {
        "blocked": 1, "ok": 96, "skipped_after_block": 31}
    olx_rows = [row for row in report["probes"] if row["source"] == "olx"]
    assert [row["status"] for row in olx_rows].count("blocked") == 1
    assert [row["status"] for row in olx_rows].count("skipped_after_block") == 31
    assert all(check["result"] == "blocked"
               for check in report["summary"]["slug_checks"]
               if check["source"] == "olx")


def test_incomplete_measurement_shape_does_not_receive_a_rank():
    selected = regions.load_catalog()["regions"][:3]
    probes = []
    for number, region in enumerate(selected):
        for source in regions.PORTALS:
            for typ in scout_regions.TYPES:
                complete_target = source != "olx" and not (
                    number == 2 and source == "otodom")
                probes.append({
                    "region": region["slug"],
                    "source": source,
                    "type": typ,
                    "status": "ok" if complete_target else "not_found",
                    # Make the partial region's sum much larger to prove that
                    # magnitude cannot move it into the comparable ranking.
                    "declared_inventory": (
                        10_000 if complete_target and number == 2
                        else 10 if complete_target else None),
                    "declared_is_minimum": False,
                })

    summary, ranking_targets = scout_regions._region_summary(selected, probes)
    by_region = {row["region"]: row for row in summary}

    assert ranking_targets == [
        "gratka/flat", "gratka/house", "morizon/flat", "morizon/house",
        "otodom/flat", "otodom/house",
    ]
    assert {
        by_region[region["slug"]]["rank"] for region in selected[:2]
    } == {1, 2}
    assert all(by_region[region["slug"]]["ranking_status"] == "comparable"
               for region in selected[:2])
    partial = by_region[selected[2]["slug"]]
    assert partial["declared_sum"] == 40_000
    assert partial["ranking_status"] == "incomplete"
    assert partial["rank"] is None

    report = {
        "generated_at": "2026-08-31T09:00:00Z",
        "scope": {
            "requests_made": len(probes),
            "request_budget": len(probes),
            "target_probes": len(probes),
            "elapsed_seconds": 0,
            "runtime_budget_seconds": 2400,
            "runtime_budget_exhausted": False,
        },
        "summary": {
            "status_counts": {"not_found": 8, "ok": 16},
            "ranking_declared_targets": ranking_targets,
            "regions": summary,
            "slug_checks": [],
        },
    }
    markdown = scout_regions.markdown_summary(report)
    assert f"| — | {partial['label']} (`{partial['region']}`)" in markdown


def test_runtime_budget_returns_partial_evidence_instead_of_timing_out():
    class Clock:
        value = 0

        def __call__(self):
            return self.value

        def sleep(self, _seconds):
            self.value += 60

    clock = Clock()
    session = Session()
    report = scout_regions.scout(
        regions.load_catalog(), session=session, delay=1, runtime_budget=30,
        sleep=clock.sleep, clock=clock, log=lambda _: None)

    assert len(session.calls) == report["scope"]["requests_made"] == 1
    assert len(report["probes"]) == 128
    assert report["scope"]["runtime_budget_exhausted"] is True
    assert report["summary"]["status_counts"] == {
        "ok": 1, "skipped_after_budget": 127}
    assert report["summary"]["ranking_declared_targets"] == []
    assert all(row["rank"] is None for row in report["summary"]["regions"])


def test_404_and_off_slug_redirect_are_bad_slug_evidence():
    region = regions.load_catalog()["regions"][0]

    class StaticSession:
        def __init__(self, response):
            self.response = response

        def get(self, *args, **kwargs):
            return self.response

    missing = scout_regions.probe(
        "gratka", "house", region,
        StaticSession(Response(404, "", "https://gratka.pl/missing")), 5)
    assert missing["status"] == "not_found"

    requested = scout_regions.search_url(
        "otodom", "flat", region["portals"]["otodom"])
    redirected = scout_regions.probe(
        "otodom", "flat", region,
        StaticSession(Response(200, _otodom_html(),
                               "https://www.otodom.pl/pl/wyniki/sprzedaz/mieszkanie")), 5)
    assert redirected["requested_url"] == requested
    assert redirected["status"] == "off_slug_redirect"
    assert redirected["declared_inventory"] is None


def test_network_error_is_recorded_without_retry():
    region = regions.load_catalog()["regions"][0]

    class BrokenSession:
        calls = 0

        def get(self, *args, **kwargs):
            self.calls += 1
            raise requests.Timeout("too slow")

    session = BrokenSession()
    row = scout_regions.probe("morizon", "house", region, session, 2)
    assert session.calls == 1
    assert row["status"] == "network_error"
    assert row["http_status"] is None
    assert "Timeout" in row["error"]


def test_report_writer_creates_json_and_readable_summary(tmp_path):
    report = scout_regions.scout(
        regions.load_catalog(), session=Session(), delay=0, sleep=lambda _: None,
        log=lambda _: None)
    output = tmp_path / "nested" / "scout.json"
    summary = tmp_path / "summary.md"
    scout_regions.write_report(report, output, summary)

    stored = json.loads(output.read_text(encoding="utf-8"))
    markdown = summary.read_text(encoding="utf-8")
    assert stored["scope"]["target_probes"] == 128
    assert "P3 nationwide one-page scout" in markdown
    assert "Nieruchomości-online was not probed" in markdown
    assert "| Rank | Region |" in markdown


def test_scout_workflow_is_manual_read_only_and_non_publishing():
    workflow = (ROOT / ".github/workflows/scout.yml").read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "\n  schedule:" not in workflow
    assert "\n  push:" not in workflow
    assert "contents: read" in workflow
    assert "git push" not in workflow
    assert "scraper.main" not in workflow
    assert "matrix:" not in workflow
    assert "group: rentgen-scrape" in workflow
    assert workflow.index("python -m pytest -q") < workflow.index(
        "python -u -m scripts.scout_regions")
    assert '"$RUNNER_TEMP/region-scout.json"' in workflow
    assert "actions/checkout@v7" in workflow
    assert "actions/setup-python@v7" in workflow
    assert "actions/upload-artifact@v7" in workflow
