"""Regression tests for the 2026-07 bug sweep. Offline — no network."""
import gzip
import json

from scraper import delist, gratka, history, morizon, olx, rcn
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
    from scraper import photomatch
    html = ('<img src="https://thumbs.cdngr.pl/thumb/abc.jpg">'
            '<img src="https://img2.morizon.pl/g/def.webp">')
    assert photomatch._EXTRACTORS["morizon"](html) == [
        "https://thumbs.cdngr.pl/thumb/abc.jpg",
        "https://img2.morizon.pl/g/def.webp"]


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
