"""Optional Chromium rehearsal of complete dry-run artifacts on two origins.

PYTHONPATH=. python tests/check_deployment_browser.py [--executable /path/to/chrome]
Requires audit-only Playwright. No outside network or remote writes are used.
"""
import argparse
import functools
import http.server
import json
import pathlib
import tempfile
import threading

from playwright.sync_api import sync_playwright

from scripts import versioned_storage as storage
from scripts.deployment_dry_run import build
from test_validate_data import _compact_dataset, _dataset
from check_storage_browser import QuietHandler, _json, _rebuild, _stats


def run(root, executable=None):
    data, store = root / "data", root / "objects"
    for slug, fixture in [("slaskie", _compact_dataset), ("opolskie", _dataset)]:
        path = data / slug
        path.mkdir(parents=True)
        fixture(path)
        _stats(path, "version-one" if slug == "slaskie" else "legacy")
    _rebuild(data / "slaskie", ["2026-01-01", "2026-02-01"])
    legacy = data / "opolskie"
    _json(legacy / "archive.json", [{"url": "https://example.test/old", "type": "flat",
          "title": "Legacy archive", "timeline": [{"date": "2026-01-01", "kind": "listed"}]}])
    first = storage.publish(data / "slaskie", store, "slaskie")
    artifact = {"site": root / "first/site"}
    ui = http.server.ThreadingHTTPServer(("127.0.0.1", 0),
        lambda *args, **kwargs: QuietHandler(*args, directory=str(artifact["site"]), **kwargs))
    base = f"http://127.0.0.1:{ui.server_port}"
    objects = http.server.ThreadingHTTPServer(("127.0.0.1", 0),
        functools.partial(storage.StorageHandler, directory=str(store), origin=base))
    object_base = f"http://127.0.0.1:{objects.server_port}"
    mapping = {"slaskie": {"pointer_url": object_base + "/slaskie/current.json"}}
    report = build(data_root=data, store=store, storage_map=mapping, output=root / "first")
    assert not (artifact["site"] / "data/slaskie").exists()
    checks = ["complete artifact omits the external payload and keeps its legacy sibling"]
    for server in [ui, objects]:
        threading.Thread(target=server.serve_forever, daemon=True).start()
    errors, requests = [], []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, **({"executable_path": executable} if executable else {}))
            context = browser.new_context()
            context.on("page", lambda page: page.on("pageerror", lambda error: errors.append(str(error))))
            context.on("request", lambda request: requests.append(request.url))
            context.route("**/*", lambda route: route.continue_() if route.request.url.startswith((base + "/", object_base + "/")) else route.abort())
            old = context.new_page()
            old.goto(base + "/region/slaskie/")
            old.wait_for_selector(".card")
            assert first["version"] in old.evaluate("DATA")
            assert not any(url.endswith("/current.json") for url in requests)
            checks.append("listing reader follows the sealed catalog without requesting the mutable pointer")
            stats = context.new_page()
            stats.goto(base + "/region/slaskie/stats/")
            stats.wait_for_function("state.data && document.querySelector('#c-dom .chart-h')")
            assert stats.evaluate("state.data.built") == "version-one"
            checks.append("external statistics render from the same sealed version")
            # Resolve every generated JSON-LD distribution.
            raw_links = old.evaluate("JSON.parse(document.querySelector('script[type=\"application/ld+json\"]').textContent)['@graph'].find(x=>x['@type']==='Dataset').distribution.map(x=>x.contentUrl)")
            assert len(raw_links) == 6
            for url in raw_links:
                response = context.request.get(url)
                assert response.ok and first["version"] in url
            checks.append("all six advertised dataset downloads resolve to immutable objects")

            _rebuild(data / "slaskie", ["2026-03-01", "2026-04-01"])
            _stats(data / "slaskie", "version-two")
            meta_path = data / "slaskie/meta.json"
            meta = json.loads(meta_path.read_bytes())
            meta["updated"] = "2026-10-19T20:30:00Z"
            _json(meta_path, meta)
            second = storage.publish(data / "slaskie", store, "slaskie")
            visitor = context.new_page()
            visitor.goto(base + "/region/slaskie/")
            visitor.wait_for_selector(".card")
            assert first["version"] in visitor.evaluate("DATA")
            checks.append("pointer advancement alone cannot mismatch the deployed catalog and new visitors")
            stats.reload()
            stats.wait_for_function("state.data && state.data.built==='version-one'")
            checks.append("statistics reload also stays on the catalog's verified version")

            # An interrupted/corrupt remote candidate must not install a new artifact.
            corrupt = store / "slaskie/versions" / second["version"] / "a/00.json"
            valid_bytes = corrupt.read_bytes()
            corrupt.unlink()
            try:
                build(data_root=data, store=store, storage_map=mapping, output=root / "failed")
                raise AssertionError("broken remote version was accepted")
            except ValueError:
                pass
            assert not (root / "failed").exists()
            visitor.reload()
            visitor.wait_for_selector(".card")
            assert first["version"] in visitor.evaluate("DATA")
            checks.append("rejected incomplete candidate leaves the previous complete artifact usable")
            corrupt.write_bytes(valid_bytes)
            build(data_root=data, store=store, storage_map=mapping, output=root / "second")
            artifact["site"] = root / "second/site"
            visitor.reload()
            visitor.wait_for_selector(".card")
            assert second["version"] in visitor.evaluate("DATA")
            assert visitor.evaluate("state.meta.updated") == meta["updated"]
            checks.append("installing a complete candidate changes catalog and data together")
            old.locator('[data-key="history"] [data-val="sold"]').click()
            old.wait_for_function("state.archive && state.archive.length===2")
            card = old.locator(".card[data-detail]").first
            key = card.get_attribute("data-detail")
            card.locator("details.tl summary").click()
            old.wait_for_function("key=>state.archiveByKey.get(key)._full", arg=key)
            assert old.evaluate("key=>state.archiveByKey.get(key).timeline[0].date", key) in ("2026-01-01", "2026-02-01")
            checks.append("a tab open across artifact publication still fetches its original timeline")

            sibling = context.new_page()
            sibling.goto(base + "/region/opolskie/")
            sibling.wait_for_selector(".card")
            assert sibling.evaluate("DATA") == "data/opolskie"
            sibling.locator('[data-key="history"] [data-val="sold"]').click()
            sibling.wait_for_function("state.archive && state.archive[0]._full")
            checks.append("legacy Pages index and full archive remain usable beside the remote region")
            sibling.goto(base + "/region/opolskie/stats/")
            sibling.wait_for_function("state.data && document.querySelector('#c-dom .chart-h')")
            assert sibling.evaluate("state.data.built") == "legacy"
            checks.append("legacy statistics render in the reduced Pages artifact")
            assert not errors, errors
            checks.append("both artifact generations and backends have no uncaught browser errors")
            browser.close()
    finally:
        for server in [ui, objects]:
            server.shutdown()
            server.server_close()
    return {"checks": checks, "pages_bytes": report["pages_bytes"], "external_bytes": report["external_bytes"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="rentgen-deployment-browser-") as temporary:
        result = run(pathlib.Path(temporary), args.executable)
    print(json.dumps(result, indent=2))
