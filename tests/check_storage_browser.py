"""Optional real-browser rehearsal; no network, portals or remote writes.

PYTHONPATH=. python tests/check_storage_browser.py [--executable /path/to/chrome]
Requires audit-only Playwright, outside the offline CI dependency set.
"""
import argparse
import functools
import http.server
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import threading

from playwright.sync_api import sync_playwright

from scraper import payload
from scripts import versioned_storage as storage
from test_validate_data import _compact_dataset, _dataset


ROOT = pathlib.Path(__file__).resolve().parents[1]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def _json(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def _stats(path, built):
    series = {name: [] for name in ("med", "active", "new", "gone", "cuts")}
    _json(path / "stats.json", {"built": built,
          "weekly": {"weeks": [], "towns": {}, "global": {"flat": series, "house": series}},
          "dom": {"buckets": [], "counts": []},
          "rcn": {"months": [], "towns": {}, "global": {}}})
    _json(path / "rcnstats.json", {})


def _rebuild(path, dates):
    rows = payload.unpack_rows(json.loads((path / "index.json").read_bytes()))
    details = {}
    for shard in (path / "d").glob("*.json"):
        details.update(json.loads(shard.read_bytes()))
    rows = [row | details[row["url"]] for row in rows]
    archive = [{"url": "same", "type": "flat", "delisted": "2026-08-01",
                "timeline": [{"kind": "listed", "date": date},
                             {"kind": "delisted", "date": "2026-08-01"}]} for date in dates]
    payload.build(rows, path, archive=archive, shards=4, log=lambda *args: None)


def run(root, executable=None):
    site = root / "site"
    shutil.copytree(ROOT / "site", site, ignore=shutil.ignore_patterns("data", "region"))
    shutil.copytree(ROOT / "scripts/templates", root / "scripts/templates")
    current = site / "data/slaskie"
    current.mkdir(parents=True)
    _compact_dataset(current)
    _rebuild(current, ["2026-01-01", "2026-02-01"])
    _stats(current, "version-one")
    legacy = site / "data/opolskie"
    legacy.mkdir()
    _dataset(legacy)
    _stats(legacy, "legacy")
    _json(legacy / "archive.json", [{"url": "https://example.test/old", "type": "flat",
          "title": "Legacy archive", "delisted": "2026-08-01", "timeline": [{"date": "2026-01-01", "kind": "listed"}]}])
    store = root / "objects"
    first = storage.publish(current, store, "slaskie")
    ui = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(site)))
    base = f"http://127.0.0.1:{ui.server_port}"
    cors = {"origin": base}
    def handler(*args, **kwargs):
        return storage.StorageHandler(*args, directory=str(store), origin=cors["origin"], **kwargs)
    objects = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    object_base = f"http://127.0.0.1:{objects.server_port}"
    catalog = json.loads((site / "regions.json").read_bytes())
    next(entry for entry in catalog["regions"] if entry["slug"] == "slaskie")["storage"] = {
        "pointer_url": object_base + "/slaskie/current.json"}
    _json(site / "regions.json", catalog)
    subprocess.run(["node", str(ROOT / "scripts/update-summary.mjs")],
                   env=os.environ | {"RENTGEN_ROOT": str(root)}, check=True, capture_output=True)
    # Only the object origin carries Śląskie bytes: accidental fallback must fail.
    shutil.move(current, root / "source")
    current = root / "source"
    servers = [ui, objects]
    for server in servers:
        threading.Thread(target=server.serve_forever, daemon=True).start()
    checks, errors, requests = [], [], []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, **({"executable_path": executable} if executable else {}))
            context = browser.new_context()
            context.on("page", lambda page: page.on("pageerror", lambda error: errors.append(str(error))))
            context.on("request", lambda request: requests.append(request.url))
            context.route("**/*", lambda route: route.continue_() if route.request.url.startswith((base + "/", object_base + "/")) else route.abort())
            old_tab = context.new_page()
            old_tab.goto(base + "/region/slaskie/")
            old_tab.wait_for_selector(".card")
            assert old_tab.evaluate("state.all.length") == 2
            assert first["version"] in old_tab.evaluate("DATA")
            checks.append("actual listing app resolves the cross-origin immutable version")
            assert not any("/a/" in url for url in requests)
            checks.append("archive details remain lazy on the new backend")

            # Change metadata and archive keys while the original tab is open.
            meta = json.loads((current / "meta.json").read_bytes())
            meta["updated"] = "2026-10-19T12:00:00Z"
            _json(current / "meta.json", meta)
            _rebuild(current, ["2026-03-01", "2026-04-01"])
            _stats(current, "version-two")
            try:
                storage.publish(current, store, "slaskie", interrupt_after=7)
                raise AssertionError("injected upload interruption did not fire")
            except InterruptedError:
                pass
            probe = context.new_page()
            probe.goto(base + "/region/slaskie/")
            probe.wait_for_selector(".card")
            assert first["version"] in probe.evaluate("DATA")
            checks.append("interrupted upload leaves new visitors on the complete previous version")
            probe.close()
            second = storage.publish(current, store, "slaskie")
            old_tab.locator('[data-key="history"] [data-val="sold"]').click()
            old_tab.wait_for_function("state.archive && state.archive.length===2")
            card = old_tab.locator(".card[data-detail]").first
            key = card.get_attribute("data-detail")
            card.locator("details.tl summary").click()
            old_tab.wait_for_function("key=>state.archiveByKey.get(key)._full", arg=key)
            assert old_tab.evaluate("key=>state.archiveByKey.get(key).timeline[0].date", key) in ("2026-01-01", "2026-02-01")
            checks.append("open tab fetches its original archive key/timeline after pointer changes")

            new_tab = context.new_page()
            new_tab.goto(base + "/region/slaskie/")
            new_tab.wait_for_selector(".card")
            assert second["version"] in new_tab.evaluate("DATA")
            assert new_tab.evaluate("state.meta.updated") == meta["updated"]
            checks.append("new visitors see the complete new version and matching metadata")
            stats = context.new_page()
            stats.goto(base + "/region/slaskie/stats/")
            stats.wait_for_function("state.data && state.data.built==='version-two'")
            assert second["version"] in stats.evaluate("DATA")
            checks.append("statistics resolve and pin the same storage protocol")

            storage.activate(store, "slaskie", first["version"])
            # The already-open new tab must retain its lazy details after rollback.
            new_tab.locator('[data-key="history"] [data-val="sold"]').click()
            new_tab.wait_for_function("state.archive && state.archive.length===2")
            card = new_tab.locator(".card[data-detail]").first
            key = card.get_attribute("data-detail")
            card.locator("details.tl summary").click()
            new_tab.wait_for_function("key=>state.archiveByKey.get(key)._full", arg=key)
            assert new_tab.evaluate("key=>state.archiveByKey.get(key).timeline[0].date", key) in ("2026-03-01", "2026-04-01")
            checks.append("rollback retains the newer version for tabs already using it")
            new_tab.reload()
            new_tab.wait_for_selector(".card")
            assert first["version"] in new_tab.evaluate("DATA")
            checks.append("reload after rollback resolves the previous version")

            legacy_tab = context.new_page()
            legacy_tab.goto(base + "/region/opolskie/")
            legacy_tab.wait_for_selector(".card")
            assert legacy_tab.evaluate("DATA") == "data/opolskie"
            legacy_tab.locator('[data-key="history"] [data-val="sold"]').click()
            legacy_tab.wait_for_function("state.archive && state.archive[0]._full")
            checks.append("legacy Pages index/full archive works beside external versioned storage")
            legacy_tab.goto(base + "/region/opolskie/stats/")
            legacy_tab.wait_for_function("state.data && state.data.built==='legacy'")
            checks.append("legacy statistics work in the mixed deployment")
            cors["origin"] = "https://wrong-origin.example"
            blocked = context.new_page()
            blocked.goto(base + "/region/slaskie/")
            blocked.get_by_text("Nie udało się wczytać danych regionu", exact=True).wait_for()
            assert blocked.locator(".card").count() == 0
            checks.append("real browser rejects incorrect CORS without falling back to stale local data")
            assert not errors, errors
            checks.append("no uncaught browser errors in either listing/statistics backend")
            browser.close()
    finally:
        for server in servers:
            server.shutdown()
            server.server_close()
    return {"checks": checks, "versions": [first["version"], second["version"]]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="rentgen-storage-browser-") as temporary:
        result = run(pathlib.Path(temporary), args.executable)
    print(json.dumps(result, indent=2))
