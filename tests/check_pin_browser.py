"""Optional Chromium checks for address lookup and copy controls.

PYTHONPATH=. .venv/bin/python tests/check_pin_browser.py [--executable /path/to/chrome]
Uses fictional data and intercepted GUGiK responses; no outside requests/writes.
Playwright is an audit dependency, separate from offline CI requirements.
"""
import argparse
import functools
import http.server
import json
import os
import pathlib
import shlex
import shutil
import subprocess
import tempfile
import threading

from playwright.sync_api import sync_playwright

from scraper import payload
from scripts.validate_data import validate_data_dir
from check_storage_browser import QuietHandler, _stats
from test_validate_data import _compact_dataset

ROOT = pathlib.Path(__file__).resolve().parents[1]
WFS = "http://www.opengis.net/wfs/2.0"
MS = "http://mapserver.gis.umn.edu/mapserver"
GEO = {"results": {"1": {"street": "Audit Street", "number": "21",
                           "x": "476458.96", "y": "269949.11"}}}


def collection(layer, *, matched=None, empty=False):
    features = ""
    if not empty and layer == "lokale":
        # The neighbouring building's deed must not attach to the chosen address.
        for number, price in [("21", 250000), ("99", 999999)]:
            features += f'''<wfs:member><ms:lokale>
                <ms:dok_data><gml:TimeInstant><gml:timePosition>2026-01-02</gml:timePosition></gml:TimeInstant></ms:dok_data>
                <ms:lok_cena_brutto>{price}</ms:lok_cena_brutto><ms:lok_pow_uzyt>50</ms:lok_pow_uzyt>
                <ms:lok_liczba_izb>3</ms:lok_liczba_izb><ms:lok_adres>MSC:Gliwice;UL:Audit Street;NR_PORZ:{number}</ms:lok_adres>
                <ms:tran_rodzaj_trans>wolnyRynek</ms:tran_rodzaj_trans><ms:tran_rodzaj_rynku>rynekWtorny</ms:tran_rodzaj_rynku>
                </ms:lokale></wfs:member>'''
    count = 2 if features else 0
    return f'''<wfs:FeatureCollection xmlns:wfs="{WFS}" xmlns:ms="{MS}" xmlns:gml="http://www.opengis.net/gml/3.2"
        numberMatched="{count if matched is None else matched}" numberReturned="{count}">{features}</wfs:FeatureCollection>'''


def run(root, executable=None):
    site = root / "site"
    shutil.copytree(ROOT / "site", site, ignore=shutil.ignore_patterns("data", "region"))
    shutil.copytree(ROOT / "scripts/templates", root / "scripts/templates")
    data = site / "data/slaskie"
    data.mkdir(parents=True)
    _compact_dataset(data)
    rows = payload.unpack_rows(json.loads((data / "index.json").read_text()))
    details = {}
    for path in (data / "d").glob("*.json"):
        details.update(json.loads(path.read_text()))
    for row in rows:
        row.update(details[row["url"]])
        row["locality"] = "Gliwice"
    payload.build(rows, data, archive=[], shards=4, log=lambda *a: None)
    meta = json.loads((data / "meta.json").read_text())
    meta.update(archive=0, sold_confirmed=0)
    (data / "meta.json").write_text(json.dumps(meta))
    _stats(data, "audit")
    validate_data_dir(data)
    subprocess.run(["node", str(ROOT / "scripts/update-summary.mjs")],
                   env=os.environ | {"RENTGEN_ROOT": str(root)}, check=True, capture_output=True)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0),
        functools.partial(QuietHandler, directory=str(site)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    checks, errors, provider_requests, pending = [], [], [], []
    mode = {"value": "success", "delay": False}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, **({"executable_path": executable} if executable else {}))
            context = browser.new_context()

            def route(request):
                url = request.request.url
                if url.startswith(base + "/"):
                    request.continue_()
                    return
                provider_requests.append(url)
                if "services.gugik.gov.pl/uug/" in url:
                    if mode["delay"]:
                        pending.append(request)
                    else:
                        request.fulfill(json=GEO)
                elif "uldk.gugik.gov.pl/" in url:
                    request.fulfill(body="0\n246601_1.0001.1|Audit precinct", content_type="text/plain")
                elif "mapy.geoportal.gov.pl/wss/service/rcn?" in url:
                    layer = "lokale" if "ms:lokale" in url else "budynki"
                    if mode["value"] == "http":
                        request.fulfill(status=503, body="unavailable")
                    elif mode["value"] == "exception":
                        request.fulfill(body='<ExceptionReport xmlns="http://www.opengis.net/ows/1.1"><Exception/></ExceptionReport>', content_type="text/xml")
                    elif mode["value"] == "xml":
                        request.fulfill(body="<broken", content_type="text/xml")
                    else:
                        request.fulfill(body=collection(layer,
                            matched=600 if mode["value"] == "partial" else None,
                            empty=mode["value"] == "empty"), content_type="text/xml")
                else:
                    raise AssertionError(f"Unexpected outside request: {url}")

            context.route("**/*", route)
            page = context.new_page()
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(base + "/region/slaskie/")
            page.wait_for_selector(".card")
            page.evaluate('''window.auditOpened = 0; window.auditCopied = [];
                window.open = () => window.auditOpened++;
                Object.defineProperty(navigator, 'clipboard', {configurable:true,
                    value:{writeText:async text=>window.auditCopied.push(text)}});''')

            def controls():
                card = page.locator(".card").first
                summary = card.locator("details.pinbox summary")
                if not card.locator("details.pinbox").evaluate("e=>e.open"):
                    summary.click()
                return card

            card = controls()
            card.locator(".pin-check").click()
            assert "podaj ulicę" in card.locator(".pin-results").inner_text()
            assert not provider_requests
            checks.append("real check click validates missing fields without a provider request")

            card.locator(".pin-ul").fill("Audit Street")
            card.locator(".pin-nr").fill("21")
            mode["delay"] = True
            card.locator(".pin-check").click()
            page.wait_for_function('document.querySelector(".card .pin-check").disabled')
            assert card.locator(".pin-results").is_visible()
            assert len(pending) == 1
            checks.append("lookup click reaches delegated handler and disables the button while pending")
            pending.pop().fulfill(json=GEO)
            mode["delay"] = False
            page.wait_for_function('!document.querySelector(".card .pin-check").disabled')
            result = card.locator(".pin-results").inner_text()
            assert "2026-01-02" in result and "250" in result and "999" not in result, result
            assert "246601_1.0001.1" in result and card.locator(".pin-links a").count() == 2
            assert len(provider_requests) == 4
            assert page.evaluate("window.auditOpened") == 0
            checks.append("successful geocoder/parcel/two-layer lookup shows only the matching building and never opens the listing")

            street = "O'Brien $(audit-only)"
            card.locator(".pin-ul").fill(street)
            card.locator(".pin-copy").click()
            page.wait_for_function("window.auditCopied.length===1")
            command = page.evaluate("window.auditCopied[0]")
            parts = shlex.split(command)
            assert parts[parts.index("--ulica") + 1] == street
            assert parts[parts.index("--nr") + 1] == "21"
            assert parts[parts.index("--pin") + 1] == card.get_attribute("data-href")
            assert page.evaluate("window.auditOpened") == 0
            checks.append("real copy click produces a correctly quoted command without opening a listing")

            dialogs = []
            def accept(dialog):
                dialogs.append(dialog.message)
                dialog.accept()
            page.on("dialog", accept)
            page.evaluate('() => {navigator.clipboard.writeText=async()=>{throw Error("clipboard denied")}}')
            card.locator(".pin-copy").click()
            assert dialogs == ["Skopiuj komendę:"]
            checks.append("clipboard refusal opens the manual copy prompt")

            # A rerender replaces the card nodes; delegated controls must survive.
            page.evaluate("resetAll()")
            card = controls()
            card.locator(".pin-ul").fill("Audit Street")
            card.locator(".pin-nr").fill("21")
            for outcome in ["http", "exception", "xml", "partial"]:
                mode["value"] = outcome
                card.locator(".pin-check").click()
                page.wait_for_function('!document.querySelector(".card .pin-check").disabled')
                result = card.locator(".pin-results").inner_text()
                assert "Nie udało się odczytać" in result and "brak aktów" not in result, result
                checks.append(f"{outcome} response shows failure, restores the button and makes no no-deeds claim")

            mode["value"] = "empty"
            card.locator(".pin-check").click()
            page.wait_for_function('!document.querySelector(".card .pin-check").disabled')
            assert "brak aktów" in card.locator(".pin-results").inner_text()
            checks.append("a valid empty response is distinct from unavailable or incomplete evidence")

            mode["delay"] = True
            page.evaluate('''() => {window.auditTimeouts=[]; const originalTimeout=AbortSignal.timeout.bind(AbortSignal);
                AbortSignal.timeout=ms=>{window.auditTimeouts.push(ms);return originalTimeout(20)};}''')
            card.locator(".pin-check").click()
            page.wait_for_function('!document.querySelector(".card .pin-check").disabled')
            assert "Nie udało się odczytać" in card.locator(".pin-results").inner_text()
            assert page.evaluate("window.auditTimeouts") == [15000]
            checks.append("a timed-out provider request restores controls and shows failure")
            for request in pending:
                request.abort()
            assert not errors, errors
            checks.append("no uncaught browser errors")
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    return {"checks": checks, "count": len(checks)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="rentgen-pin-browser-") as temporary:
        print(json.dumps(run(pathlib.Path(temporary), args.executable), indent=2))
