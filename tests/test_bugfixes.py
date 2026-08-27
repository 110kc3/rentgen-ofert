"""Regression tests for the 2026-07 bug sweep. Offline — no network."""
import gzip
import json
import pathlib

from scraper import coverage, delist, gratka, history, morizon, olx, rcn
from scraper import nieruchomosci_online as nol
from scraper.normalize import location_parts


# ---- delist ------------------------------------------------------------------

def test_gone_marker_ignores_ordinary_prose():
    # "zakończone" in a live ad's description must not mark it dead
    assert not delist._GONE_MARKERS.search(
        "Prace remontowe zostały zakończone w 2024 roku.")
    assert delist._GONE_MARKERS.search("Ogłoszenie zakończone")
    assert delist._GONE_MARKERS.search("oferta zakończona")


def test_last_seen_ignores_archived_observations():
    rec = {"first_seen": "2026-06-01",
           "observations": [
               {"date": "2026-06-01", "url": "u1", "price": 1},
               {"date": "2026-06-10", "url": "u1", "status": "archived"}]}
    assert delist.last_seen(rec) == "2026-06-01"


def test_sweep_preserves_archived_delisting_same_run():
    # observe_archived marks delisted=today; the sweep that runs right after
    # must not clear it just because the record was live within the grace window
    records = []
    history.update([dict(type="flat", area=50.0, url="u1", price=1,
                         source="olx", phashes=[3], offers=[])],
                   records, "2026-06-08")
    history.observe_archived([dict(type="flat", area=50.0, url="u1",
                                   archived=True)], records, "2026-06-10")
    assert records[0]["delisted"] == "2026-06-10"

    class _S:  # any URL check would say "live" — must not even get there
        def get(self, url, **kw):
            raise AssertionError("no URL should be checked")

    delist.sweep(records, "2026-06-10", _S(), active_urls=set(), log=lambda *a: None)
    assert records[0]["delisted"] == "2026-06-10"


def test_sweep_sort_survives_equal_keys():
    obs = [{"date": "2026-01-01", "url": "same", "price": 1}]
    records = [{"type": "flat", "area": 50.0, "first_seen": "2026-01-01",
                "observations": list(obs)},
               {"type": "flat", "area": 50.0, "first_seen": "2026-01-01",
                "observations": list(obs)}]

    class _S:
        def get(self, url, **kw):
            class R:
                status_code, text, url_, history = 404, "", "", []
                url = ""
            return R()

    # two candidates tie on (seen, url) — sorting must not compare the dicts
    delist.sweep(records, "2026-06-01", _S(), active_urls=set(), log=lambda *a: None)


# ---- history: relist semantics -------------------------------------------------

def _flat(**kw):
    base = dict(type="flat", area=48.0, url="https://otodom.pl/a", price=400000,
                source="otodom", phashes=[7], offers=[])
    base.update(kw)
    return base


def test_portal_dropoff_is_not_a_relist():
    records = []
    two_offers = [{"source": "otodom", "url": "https://otodom.pl/a", "price": 400000},
                  {"source": "olx", "url": "https://olx.pl/b", "price": 390000}]
    history.update([_flat(offers=list(two_offers))], records, "2026-06-01")
    # the OLX ad expires; the flat stays live on Otodom — NOT a relist
    p = _flat(offers=[two_offers[0]])
    history.update([p], records, "2026-06-05")
    assert len(records) == 1
    assert p["relisted"] is False
    assert p["prev_price"] is None


def test_repost_under_new_url_is_a_relist():
    records = []
    history.update([_flat()], records, "2026-06-01")
    p = _flat(url="https://otodom.pl/new", price=380000)
    history.update([p], records, "2026-06-10")
    assert p["relisted"] is True
    assert p["prev_price"] == 400000


def test_all_offers_observed_and_price_trail_uses_min():
    records = []
    offers = [{"source": "otodom", "url": "u-oto", "price": 500000},
              {"source": "olx", "url": "u-olx", "price": 480000}]
    p = _flat(url="u-oto", price=480000, offers=offers)
    history.update([p], records, "2026-06-01")
    urls = {o["url"] for o in records[0]["observations"]}
    assert urls == {"u-oto", "u-olx"}
    # cheaper OLX offer gone -> card price rises to 500k; that IS a trail point,
    # but no phantom "price change" is invented for u-oto itself
    p2 = _flat(url="u-oto", price=500000, offers=[offers[0]])
    history.update([p2], records, "2026-06-08")
    assert p2["relisted"] is False
    assert p2["price_history"] == [{"date": "2026-06-01", "price": 480000},
                                   {"date": "2026-06-08", "price": 500000}]


# ---- history: storage safety ---------------------------------------------------

def test_history_load_missing_ok_corrupt_raises(tmp_path):
    assert history.load(tmp_path / "absent.json") == []
    bad = tmp_path / "bad.json"
    bad.write_text('[{"truncated": ', encoding="utf-8")
    try:
        history.load(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("corrupt history must fail loudly, not wipe the store")


def test_history_save_is_atomic(tmp_path):
    path = tmp_path / "history.json"
    history.save(path, [{"a": 1}])
    assert json.loads(path.read_text(encoding="utf-8")) == [{"a": 1}]
    assert not path.with_name(path.name + ".tmp").exists()


def test_history_gzip_roundtrip_and_legacy_fallback(tmp_path):
    gz = tmp_path / "history.json.gz"
    history.save(gz, [{"a": "ł"}])
    with gzip.open(gz, "rt", encoding="utf-8") as f:
        assert json.load(f) == [{"a": "ł"}]
    assert history.load(gz) == [{"a": "ł"}]
    # a pre-gzip plain history.json is picked up when the .gz doesn't exist yet
    legacy_dir = tmp_path / "legacy"
    legacy_dir.mkdir()
    (legacy_dir / "history.json").write_text('[{"b": 2}]', encoding="utf-8")
    assert history.load(legacy_dir / "history.json.gz") == [{"b": 2}]


# ---- scrapers ------------------------------------------------------------------

def test_olx_state_regex_survives_escaped_quotes():
    payload = json.dumps(json.dumps(
        {"listing": {"listing": {"ads": [], "totalPages": 1}},
         "noise": 'ogrodzenie \\"kute\\"; garaż'}))
    html = f"<script>window.__PRERENDERED_STATE__ = {payload};</script>"
    state = olx.extract_state(html)
    assert state["listing"]["listing"]["totalPages"] == 1


def test_location_parts_strips_any_voivodeship():
    assert location_parts("Krowodrza, Kraków, małopolskie") == ["Krowodrza", "Kraków"]
    assert location_parts("Krowodrza, Kraków, woj. małopolskie") == ["Krowodrza", "Kraków"]
    assert location_parts("Żerniki, Gliwice, śląskie") == ["Żerniki", "Gliwice"]
    assert gratka._locality("Krowodrza, Kraków, małopolskie") == "Kraków"
    assert gratka._district("Krowodrza, Kraków, małopolskie") == "Krowodrza"
    assert morizon._locality("Stare Miasto, Wrocław, dolnośląskie") == "Wrocław"


def test_nol_town_slug_gets_proper_name():
    """A sub-domain slug must never be title-cased into a locality: "Dabrowa-
    Gornicza" would split dedupe/geocoding keys away from "Dąbrowa Górnicza".
    Display names come from the resolved town map; an unmapped slug yields no
    locality at all rather than an invented one."""
    towns = nol.SEED_TOWNS["slaskie"]
    offer = {"url": "https://x/dom,na-sprzedaz/1.html", "price": "500000",
             "itemOffered": {}}
    named = nol.parse_offers([offer], "house", "dabrowa-gornicza", towns)
    assert named[0]["locality"] == "Dąbrowa Górnicza"
    assert nol.parse_offers([offer], "house", "bielsko-biala", towns)[0]["locality"] \
        == "Bielsko-Biała"
    assert nol.parse_offers([offer], "house", "unknown-town", towns)[0]["locality"] is None


def test_morizon_has_photo_extractor():
    """Pinned to real pages, not to invented URLs — see tests/test_photomatch.py.

    The previous version of this test asserted against two made-up URLs, so it
    passed happily for however long morizon was serving its galleries from a
    host the extractor didn't match and returning zero hashes for every ad.
    """
    from scraper import photomatch
    html = (pathlib.Path(__file__).parent / "fixtures" / "morizon_detail.html"
            ).read_text(encoding="utf-8")
    urls = photomatch._EXTRACTORS["morizon"](html)
    assert urls, "morizon must extract SOMETHING from a real detail page"
    assert all("staticmorizon.com.pl" in u for u in urls)


# ---- rcn -----------------------------------------------------------------------

def test_fold_collapses_whitespace():
    assert rcn._fold("Bielsko - Biała") == rcn._fold("Bielsko-Biała") == "bielsko biala"
    assert rcn._fold(" Katowice  ") == "katowice"


def test_building_number_spacing_not_decisive_mismatch():
    rec = {"type": "flat", "area": 48.0}
    snap = {"street": "Gdańska", "nr": "13 A"}
    deed = {"a": 48.0, "ul": "Gdańskiej", "nr": "13A"}
    conf, ok = rcn._score(rec, snap, deed, is_flat=True)
    assert (conf, ok) == (2, True)


def test_street_declension_rejects_agent_nouns():
    # case forms of the same name still match ...
    assert rcn.street_match("Gdańska", "Gdańskiej")
    assert rcn.street_match("Polna", "Polnej")
    assert rcn.street_match("Asnyka", "Adama Asnyka")
    # ... but a different word with a shared prefix does not
    assert not rcn.street_match("Górna", "Górnika")
    assert not rcn.street_match("Leśna", "Leśnika")
    assert not rcn.street_match("Wodna", "Wodnika")


def test_snapshot_roundtrip_atomic(tmp_path):
    path = tmp_path / "snap.json.gz"
    rcn.save_snapshot(path, {"fetched": "2026-07-11", "lokale": [], "budynki": []})
    with gzip.open(path, "rt", encoding="utf-8") as f:
        assert json.load(f)["fetched"] == "2026-07-11"
    assert not path.with_name(path.name + ".tmp").exists()


# ---- net: bounded retry sleeps ---------------------------------------------------

def test_retry_after_is_capped():
    from types import SimpleNamespace
    from scraper import net
    r = net.CappedRetry(total=5, respect_retry_after_header=True)
    resp = SimpleNamespace(headers={"Retry-After": "86400"})   # portal says: a day
    assert r.get_retry_after(resp) == net.RETRY_AFTER_CAP
    resp_small = SimpleNamespace(headers={"Retry-After": "3"})
    assert r.get_retry_after(resp_small) == 3.0
    assert r.get_retry_after(SimpleNamespace(headers={})) is None


def test_a_transient_405_is_retried_not_fatal():
    """Otodom refuses with 405, not 429: band `300k-400k` died at page 5 and
    the next seven died on page 1 before the eighth was served normally (runs
    31408840562, 31422141701). Not in `status_forcelist`, the refusal was
    fatal on first contact with no back-off at all."""
    from scraper import net
    s = net.session()
    forced = s.adapters["https://"].max_retries.status_forcelist
    assert 405 in forced and 429 in forced
    assert 404 not in forced, "a missing page is an answer, not a refusal"


# ---- olx: a refusal and a re-skin are different bugs -----------------------------

def test_a_missing_state_blob_is_fingerprinted_not_guessed_at():
    """`__PRERENDERED_STATE__ not found (layout changed?)` was a guess, and on
    2026-08-11 the wrong one twice: OLX served that on page 1 of both searches
    50 s after the previous run walked 518 of its pages. Blocked vs re-skinned
    need opposite fixes, and the run log is all CI keeps."""
    class _Resp:
        status_code = 200
        text = ('<html><head><title>Access denied | olx.pl</title></head>'
                '<body>Please complete the captcha. datadome</body></html>')
    fp = olx.fingerprint(_Resp())
    assert "HTTP 200" in fp and "Access denied | olx.pl" in fp
    assert "captcha" in fp and "datadome" in fp
    assert "olx.pl" in fp.split("olx-markers=")[1]     # it IS an OLX page

    class _Reskin:
        status_code = 200
        text = ('<html><head><title>Mieszkania na sprzedaż</title></head>'
                '<body><script id="__NEXT_DATA__">{}</script></body></html>')
    fp = olx.fingerprint(_Reskin())
    assert "challenge=none" in fp, "no bot wall here — this one really is a re-skin"
    assert "__NEXT_DATA__" in fp


def test_the_walk_logs_what_the_page_was():
    class _Blocked:
        status_code = 200
        text = "<html><title>Just a moment...</title>cf-chl</html>"

        def raise_for_status(self):
            pass

    class _Session:
        def get(self, url, **kw):
            return _Blocked()

    said = []
    out = olx.scrape(max_pages=2, delay=0, session=_Session(),
                     log=said.append, types=("flat",), banded=False)
    assert out == []
    line = [m for m in said if "error" in m][0]
    assert "Just a moment..." in line and "cf-chl" in line and "HTTP 200" in line
    assert olx.scrape.last_coverage[0]["stopped"] == "error"


def test_photo_budget_skips_uncached(monkeypatch):
    from scraper import photomatch
    fetched = []
    monkeypatch.setattr(photomatch, "listing_hashes",
                        lambda l, s: (fetched.append(l["url"]) or ([1], ["u"])))
    listings = [{"source": "olx", "url": f"u{i}"} for i in range(4)]
    photomatch.attach_hashes(listings, session=object(), log=lambda *a: None,
                             budget_s=-1)          # budget already exhausted
    assert fetched == []                            # nothing fetched...
    assert all(l["phashes"] == [] for l in listings)
    photomatch.attach_hashes(listings, session=object(), log=lambda *a: None)
    assert len(fetched) == 4                        # ...but unlimited still works


# ---- marketstats ---------------------------------------------------------------

def test_withdrawal_week_is_on_axis_without_live_obs():
    from scraper import marketstats
    records = [{"type": "house", "area": 120.0, "first_seen": "2026-06-16",
                "delisted": "2026-06-24",
                "observations": [{"date": "2026-06-16", "price": 500000, "url": "u"}]}]
    out = marketstats.build(records, None, "2026-07-01")["weekly"]
    weeks = out["weeks"]
    gone = out["global"]["house"]["gone"]
    assert "2026-06-22" in weeks           # the delisting's week exists on the axis
    assert gone[weeks.index("2026-06-22")] == 1


def test_nol_dedupes_cross_listed_towns_by_ad_id():
    """Every n-online town sub-domain serves its neighbours' offers under its
    own hostname, so one ad arrives as gliwice.…/123.html AND katowice.…/123.html.
    Keying `seen` on the URL made every page look fresh: 58 613 rows collapsing
    to 11 172 properties in the 2026-08-08 run, the `dup_pages` exit never
    firing, and 75 of the run's 123 scrape minutes spent to gain 83 listings.
    """
    ids = [26859971, 26684311, 26850845]

    class _Sess:
        def __init__(self):
            self.calls = 0

        def get(self, url, **kw):
            self.calls += 1
            town = url.split("//")[1].split(".")[0]
            # every town serves the same three ads, under its own hostname
            offers = [{"url": f"https://{town}.nieruchomosci-online.pl/x/{i}.html",
                       "price": "500000", "itemOffered": {"floorSize": {"value": 50}}}
                      for i in ids]

            class R:
                status_code = 200
                text = json.dumps(offers)

                @staticmethod
                def raise_for_status():
                    pass
            return R()

    monkey = nol.extract_offers
    nol.extract_offers = json.loads
    try:
        s = _Sess()
        out = nol.scrape(max_pages=50, delay=0, session=s, log=lambda *a: None,
                         types=("flat",),
                         towns={"gliwice": "Gliwice", "katowice": "Katowice",
                                "zabrze": "Zabrze"})
    finally:
        nol.extract_offers = monkey

    # one property per ad id, not one per (town, ad) pair
    assert len(out) == len(ids)
    assert {l["source_id"] for l in out} == {str(i) for i in ids}
    # and the duplicate-page guard now fires, so towns 2 and 3 stop early
    # instead of walking to the cap
    assert s.calls <= 3 * 3, f"walked {s.calls} pages for 3 towns of duplicates"


def test_nol_refusal_is_blocked_not_a_clean_zero():
    class _Refused:
        @staticmethod
        def get(*args, **kwargs):
            raise IOError("403 Client Error: Forbidden")

    assert nol.scrape(max_pages=5, delay=0, session=_Refused(),
                      log=lambda *a: None, types=("flat",),
                      towns={"gliwice": "Gliwice"}) == []
    row = nol.scrape.last_coverage[0]
    assert row["stopped"] == coverage.ERROR and row["http_status"] == 403
    health = coverage.summarise([row])["by_source"]["nieruchomosci-online"]
    assert health["status"] == coverage.BLOCKED


def test_nol_without_resolved_towns_is_unknown_not_a_clean_zero():
    nol.scrape(max_pages=5, delay=0, session=object(), log=lambda *a: None,
               types=("flat",), towns={})
    row = nol.scrape.last_coverage[0]
    assert row["unknown"] is True
    health = coverage.summarise([row])["by_source"]["nieruchomosci-online"]
    assert health["status"] == coverage.UNKNOWN


class _NolPages:
    def __init__(self, pages):
        self.pages = pages
        self.urls = []

    def get(self, url, **kwargs):
        self.urls.append(url)
        page = int(url.rsplit("?p=", 1)[1]) if "?p=" in url else 1
        offers = self.pages.get(page, [])

        class Response:
            status_code = 200
            text = json.dumps(offers)

            @staticmethod
            def raise_for_status():
                pass

        return Response()


def _nol_offer(source_id, archived=False):
    availability = "OutOfStock" if archived else "InStock"
    return {
        "url": f"https://katowice.nieruchomosci-online.pl/x/{source_id}.html",
        "availability": f"https://schema.org/{availability}",
        "price": "500000",
        "itemOffered": {"floorSize": {"value": 50}},
    }


def test_nol_active_pass_stops_at_confirmed_archive_boundary(monkeypatch):
    """Current offers are sorted before the archive. Normal runs confirm that
    boundary twice, discard the archive rows, and retain the last harvest's
    count/date instead of walking it again twice daily.
    """
    monkeypatch.setattr(nol, "extract_offers", json.loads)
    session = _NolPages({
        1: [_nol_offer(1), _nol_offer(2)],
        2: [_nol_offer(10, archived=True)],
        3: [_nol_offer(11, archived=True)],
        4: [_nol_offer(12, archived=True)],
    })
    state = {
        "schema": 1, "refreshed": "2026-08-24", "records": 99,
        "complete": False,
        "by_type": {"flat": {"archived": 99, "current": 2}},
    }
    out = nol.scrape(
        max_pages=20, delay=0, session=session, log=lambda *a: None,
        types=("flat",), towns={"katowice": "Katowice"},
        harvest_archive=False, archive_state=state,
        today="2026-08-25", archive_only_pages=2)

    assert {row["source_id"] for row in out} == {"1", "2"}
    assert len(session.urls) == 3
    row = nol.scrape.last_coverage[0]
    assert row["stopped"] == coverage.OK
    assert row["current"] == 2 and row["archived"] == 0
    assert row["towns"]["katowice"]["stop"] == "archive_boundary"
    assert row["towns"]["katowice"]["served_archived"] == 2
    assert row["archive_harvest"] == {
        "mode": "cached", "refreshed": "2026-08-24",
        "records": 99, "complete": False,
    }

    source = coverage.summarise([row])["by_source"]["nieruchomosci-online"]
    assert source["status"] == coverage.HEALTHY
    assert source["archive_harvest"]["records"] == 99
    assert source["types"]["flat"]["partitions"]["axis"] == "town"
    assert source["types"]["flat"]["partitions"]["details"]["katowice"][
        "stop"] == "archive_boundary"


def test_nol_full_archive_harvest_names_the_capped_town(monkeypatch):
    monkeypatch.setattr(nol, "extract_offers", json.loads)
    session = _NolPages({
        1: [_nol_offer(1), _nol_offer(10, archived=True)],
        2: [_nol_offer(11, archived=True)],
    })
    out = nol.scrape(
        max_pages=2, delay=0, session=session, log=lambda *a: None,
        types=("flat",), towns={"katowice": "Katowice"},
        harvest_archive=True, today="2026-08-25")

    assert sum(bool(row.get("archived")) for row in out) == 2
    row = nol.scrape.last_coverage[0]
    assert row["stopped"] == coverage.OUR_CAP
    assert row["capped_partitions"] == ["katowice"]
    warning = coverage.warnings([row])[0]
    assert "capped partition(s): katowice" in warning
    parts = coverage.summarise([row])["by_source"][
        "nieruchomosci-online"]["types"]["flat"]["partitions"]
    assert parts["capped"] == ["katowice"] and parts["complete"] == 0
    assert nol.scrape.last_archive_state["records"] == 2
    assert nol.scrape.last_archive_state["complete"] is False


def test_nol_archive_cadence_bootstraps_from_previous_meta(tmp_path):
    meta = tmp_path / "meta.json"
    meta.write_text(json.dumps({
        "updated": "2026-08-24T09:54:34+00:00",
        "coverage": {
            "by_source": {"nieruchomosci-online": {"types": {
                "flat": {"current": 8, "archived": 38, "pages": 20},
                "house": {"current": 2, "archived": 9, "pages": 5},
            }}},
            "issues": [{
                "source": "nieruchomosci-online", "type": "flat",
                "capped_partitions": ["katowice"],
            }],
        },
    }), encoding="utf-8")
    state_path = tmp_path / "nol_archive.json"
    state = nol.load_archive_state(state_path, meta)

    assert state["refreshed"] == "2026-08-24" and state["records"] == 47
    assert state["complete"] is False
    assert state["by_type"]["flat"]["capped"] == ["katowice"]
    assert not nol.archive_due(state, "2026-08-30", "auto", interval_days=7)
    assert nol.archive_due(state, "2026-08-31", "auto", interval_days=7)
    assert nol.archive_due(state, "2026-08-24", "force", interval_days=7)
    assert not nol.archive_due({}, "2026-08-24", "skip", interval_days=7)

    nol.save_archive_state(state_path, state)
    assert nol.load_archive_state(state_path) == state
