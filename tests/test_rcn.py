"""RCN: GML parsing, compaction, street matching and sale attachment. Offline."""
from scraper import rcn
import pytest

GML_PAGE = """<?xml version='1.0' encoding="UTF-8" ?>
<wfs:FeatureCollection
   xmlns:ms="http://mapserver.gis.umn.edu/mapserver"
   xmlns:gml="http://www.opengis.net/gml/3.2"
   xmlns:wfs="http://www.opengis.net/wfs/2.0"
   numberMatched="unknown" numberReturned="1">
  <wfs:member>
    <ms:lokale gml:id="lokale.1">
      <ms:teryt>2466</ms:teryt>
      <ms:tran_rodzaj_trans>wolnyRynek</ms:tran_rodzaj_trans>
      <ms:tran_rodzaj_rynku>wtorny</ms:tran_rodzaj_rynku>
      <ms:tran_cena_brutto>329333.49</ms:tran_cena_brutto>
      <ms:dok_data>2021-07-13 02:00:00+02</ms:dok_data>
      <ms:lok_funkcja>mieszkalna</ms:lok_funkcja>
      <ms:lok_liczba_izb>2</ms:lok_liczba_izb>
      <ms:lok_nr_kond>3</ms:lok_nr_kond>
      <ms:lok_pow_uzyt>39.4</ms:lok_pow_uzyt>
      <ms:lok_cena_brutto></ms:lok_cena_brutto>
      <ms:lok_adres>MSC:Gliwice;UL:Adama Asnyka;NR_PORZ:11</ms:lok_adres>
    </ms:lokale>
  </wfs:member>
</wfs:FeatureCollection>"""


def test_parse_and_compact_lokale():
    rows = list(rcn._parse_members(GML_PAGE.encode(), "lokale"))
    assert len(rows) == 1
    c = rcn._compact_lok(rows[0])
    assert c == {"d": "2021-07-13", "c": 329333, "a": 39.4, "izb": 2, "kond": 3,
                 "rynek": "w", "msc": "Gliwice", "ul": "Adama Asnyka", "nr": "11"}


def test_compact_drops_non_market_and_priceless():
    row = {"dok_data": "2021-01-01", "tran_cena_brutto": "100",
           "lok_pow_uzyt": "40", "tran_rodzaj_trans": "przetarg"}
    assert rcn._compact_lok(row) is None
    row2 = {"dok_data": "2021-01-01", "lok_pow_uzyt": "40",
            "tran_rodzaj_trans": "wolnyRynek"}
    assert rcn._compact_lok(row2) is None


def test_street_match():
    assert rcn.street_match("Asnyka", "Adama Asnyka")
    assert rcn.street_match("ul. Gdańska", "Gdanska")
    assert rcn.street_match("al. Wojciecha Korfantego", "Korfantego")
    assert not rcn.street_match("Polna", "Lipowa")
    assert not rcn.street_match("Jana Pawła II", "Jana Kochanowskiego")
    assert not rcn.street_match("", "Gdańska")


def _rec(**kw):
    base = {"type": "flat", "area": 39.4, "first_seen": "2026-06-01",
            "observations": [],
            "snapshot": {"locality": "Gliwice", "street": "Asnyka",
                         "rooms": 2, "floor": 2}}
    base.update(kw)
    return base


def _tx(**kw):
    base = {"d": "2021-07-13", "c": 329333, "a": 39.4, "izb": 2, "kond": 3,
            "rynek": "w", "msc": "Gliwice", "ul": "Adama Asnyka", "nr": "11"}
    base.update(kw)
    return base


def test_match_past_sale_high_confidence():
    rec = _rec()
    snap = {"lokale": [_tx()], "budynki": []}
    assert rcn.match([rec], snap, log=lambda *a: None) == 1
    (s,) = rec["sales"]
    assert s["kind"] == "past" and s["price"] == 329333 and s["confidence"] == "wysoka"
    assert s["price_m2"] == round(329333 / 39.4)


def test_match_sold_after_delisting():
    rec = _rec(delisted="2026-06-15")
    snap = {"lokale": [_tx(d="2026-07-20", c=310000)], "budynki": []}
    rcn.match([rec], snap, log=lambda *a: None)
    kinds = {s["kind"] for s in rec["sales"]}
    assert "sold" in kinds


def test_no_match_when_street_differs():
    rec = _rec()
    snap = {"lokale": [_tx(ul="Lipowa")], "budynki": []}
    assert rcn.match([rec], snap, log=lambda *a: None) == 0
    assert "sales" not in rec


def test_no_street_attribute_and_uniqueness_rules():
    rec = _rec(snapshot={"locality": "Gliwice", "rooms": 2, "floor": 2})
    # kond 3 == floor 2 + 1 (parter=1) -> attribute-anchored match
    snap = {"lokale": [_tx(ul=None)], "budynki": []}
    assert rcn.match([rec], snap, log=lambda *a: None) == 1
    assert rec["sales"][0]["confidence"] == "średnia"
    # rooms-only IS enough when the area is decimal (39.4) and the deed is the
    # town's only candidate...
    rec2 = _rec(snapshot={"locality": "Gliwice", "rooms": 2})
    assert rcn.match([rec2], snap, log=lambda *a: None) == 1
    # ...but not when the area is a round number (weak identity)
    rec3 = _rec(area=39.0, snapshot={"locality": "Gliwice", "rooms": 2})
    snap3 = {"lokale": [_tx(ul=None, a=39.0)], "budynki": []}
    assert rcn.match([rec3], snap3, log=lambda *a: None) == 0
    # ...and never when a known attribute disagrees
    rec4 = _rec(snapshot={"locality": "Gliwice", "rooms": 4})
    assert rcn.match([rec4], snap, log=lambda *a: None) == 0


def test_street_declension_matches():
    assert rcn.street_match("ul. Gdańskiej", "Gdańska")
    assert rcn.street_match("Lipowej", "Lipowa")
    assert not rcn.street_match("Kwiatowa", "Kwiatkowskiego")


def test_house_plot_corroboration():
    rec = _rec(type="house", area=141.5,
               snapshot={"locality": "Pyskowice", "plot_area": 800})
    snap = {"lokale": [], "budynki": [
        {"d": "2020-05-05", "c": 610000, "a": 141.5, "grunt": 812.0,
         "rynek": "w", "msc": "Pyskowice", "ul": None, "nr": None}]}
    assert rcn.match([rec], snap, log=lambda *a: None) == 1
    # plot off by >10% -> no match
    rec2 = _rec(type="house", area=141.5,
                snapshot={"locality": "Pyskowice", "plot_area": 400})
    assert rcn.match([rec2], snap, log=lambda *a: None) == 0


def test_area_tolerance():
    rec = _rec()
    snap = {"lokale": [_tx(a=41.2)], "budynki": []}   # 1.8 m2 off -> no match
    assert rcn.match([rec], snap, log=lambda *a: None) == 0


def test_ambiguous_sold_not_attached():
    rec = _rec(delisted="2026-06-15")
    snap = {"lokale": [_tx(d="2026-07-20"), _tx(d="2026-08-02", nr="13")],
            "budynki": []}
    rcn.match([rec], snap, log=lambda *a: None)
    assert not any(s["kind"] == "sold" for s in rec.get("sales", []))


def test_pinned_number_is_decisive():
    # street+nr agree -> wysoka, even if rooms/floor unknown
    rec = _rec(snapshot={"locality": "Gliwice", "street": "Asnyka", "nr": "11"})
    snap = {"lokale": [_tx()], "budynki": []}
    assert rcn.match([rec], snap, log=lambda *a: None) == 1
    assert rec["sales"][0]["confidence"] == "wysoka"
    # street agrees but number differs -> reject
    rec2 = _rec(snapshot={"locality": "Gliwice", "street": "Asnyka", "nr": "13"})
    assert rcn.match([rec2], snap, log=lambda *a: None) == 0


def test_arealess_deed_needs_street_and_nr():
    deed = _tx(a=None)
    # with pinned street+nr -> matches despite missing deed area
    rec = _rec(snapshot={"locality": "Gliwice", "street": "Asnyka", "nr": "11"})
    assert rcn.match([rec], {"lokale": [deed], "budynki": []},
                     log=lambda *a: None) == 1
    # without a pinned nr the area-less deed is never considered
    rec2 = _rec(snapshot={"locality": "Gliwice", "street": "Asnyka"})
    assert rcn.match([rec2], {"lokale": [deed], "budynki": []},
                     log=lambda *a: None) == 0


def test_parcel_extraction_and_decisive_scoring():
    assert rcn._parcel("221104_4.0004.921_BUD.22_LOK") == "221104_4.0004.921"
    assert rcn._parcel("246601_1.0041.1506") == "246601_1.0041.1506"
    assert rcn._parcel("") is None
    # same parcel -> wysoka even with nothing else known
    rec = _rec(snapshot={"locality": "Gliwice", "dzialka_id": "246601_1.0041.1506"})
    snap = {"lokale": [_tx(ul=None, nr=None, dz="246601_1.0041.1506")], "budynki": []}
    assert rcn.match([rec], snap, log=lambda *a: None) == 1
    assert rec["sales"][0]["confidence"] == "wysoka"
    # different parcel + no street agreement -> reject
    rec2 = _rec(snapshot={"locality": "Gliwice", "dzialka_id": "246601_1.0041.9999"})
    assert rcn.match([rec2], snap, log=lambda *a: None) == 0


def test_renumbered_parcel_street_nr_still_wins():
    # 2008 deed on działka 974; today's ULDK says 1506 (renumbered). The
    # street+number agreement must override the parcel mismatch.
    deed = _tx(a=None, ul="Ignacego Daszyńskiego", nr="448", dz="246601_1.0041.974")
    rec = _rec(type="house", area=204.0,
               snapshot={"locality": "Gliwice", "street": "Ignacego Daszyńskiego",
                         "nr": "448", "dzialka_id": "246601_1.0041.1506"})
    assert rcn.match([rec], {"lokale": [], "budynki": [deed]},
                     log=lambda *a: None) == 1
    assert rec["sales"][0]["confidence"] == "wysoka"


@pytest.mark.parametrize("anchor", ["street", "number", "parcel"])
@pytest.mark.parametrize("conflict", [{"izb": 4}, {"kond": 8}])
def test_address_evidence_cannot_override_conflicting_flat_attributes(anchor, conflict):
    rec = _rec(delisted="2026-06-15")
    deed = _tx(d="2026-07-20", **conflict)
    if anchor == "number":
        rec["snapshot"]["nr"] = "11"
    if anchor == "parcel":
        rec["snapshot"]["dzialka_id"] = deed["dz"] = "246601_1.0041.1506"
    assert rcn.match([rec], {"lokale": [deed], "budynki": []},
                     log=lambda *a: None) == 0
    assert "sales" not in rec


@pytest.mark.parametrize("change", ["ambiguous", "empty", "attributes", "location", "development"])
def test_previously_attached_sale_is_reconciled_when_evidence_changes(change):
    rec = _rec(delisted="2026-06-15")
    deed = _tx(d="2026-07-20")
    snap = {"lokale": [deed], "budynki": []}
    assert rcn.match([rec], snap, log=lambda *a: None) == 1
    assert rec["sales"][0]["kind"] == "sold"
    if change == "ambiguous":
        snap["lokale"].append(_tx(d="2026-08-02", nr="13"))
    elif change == "empty":
        snap["lokale"] = []
    elif change == "attributes":
        rec["snapshot"]["rooms"] = 4
    elif change == "location":
        rec["snapshot"]["locality"] = "Częstochowa"
    else:
        rec["development"] = True
    assert rcn.match([rec], snap, log=lambda *a: None) == 0
    assert "sales" not in rec


@pytest.mark.parametrize("unavailable", [None, {}, {"budynki": []}, {"lokale": None}])
def test_unavailable_snapshot_or_layer_preserves_existing_evidence(unavailable):
    rec = _rec()
    snap = {"lokale": [_tx()], "budynki": []}
    rcn.match([rec], snap, log=lambda *a: None)
    previous = rec["sales"]
    rcn.match([rec], unavailable, log=lambda *a: None)
    assert rec["sales"] == previous


def test_ambiguous_sold_retraction_preserves_supported_past_deeds():
    rec = _rec(delisted="2026-06-15")
    snap = {"lokale": [_tx(), _tx(d="2026-07-20")], "budynki": []}
    rcn.match([rec], snap, log=lambda *a: None)
    assert {s["kind"] for s in rec["sales"]} == {"past", "sold"}
    snap["lokale"].append(_tx(d="2026-08-02", nr="13"))
    rcn.match([rec], snap, log=lambda *a: None)
    assert {s["kind"] for s in rec["sales"]} == {"past"}


def test_invalid_snapshot_fails_before_retracting_any_claim():
    rec = _rec()
    rcn.match([rec], {"lokale": [_tx()]}, log=lambda *a: None)
    previous = rec["sales"]
    with pytest.raises(ValueError, match="budynki"):
        rcn.match([rec], {"lokale": [], "budynki": "invalid"}, log=lambda *a: None)
    assert rec["sales"] == previous


def test_rcn_refresh_failure_preserves_cached_evidence(tmp_path, monkeypatch):
    path = tmp_path / "rcn.json.gz"
    snapshot = {"fetched": "2026-06-01", "lokale": [_tx()], "budynki": [_tx()]}
    rcn.save_snapshot(path, snapshot)

    def unavailable(*args, **kwargs):
        raise OSError("offline fixture")

    monkeypatch.setattr(rcn, "fetch_all", unavailable)
    assert rcn.refresh(path, None, today="2026-09-05", log=lambda *a: None) == snapshot
    assert rcn.refresh(tmp_path / "missing.gz", None, today="2026-09-05",
                       log=lambda *a: None) is None


def _page(rows=1, *, total="unknown", next_page=False, ident=1, uppercase=False):
    import xml.etree.ElementTree as ET
    root = ET.fromstring(GML_PAGE)
    member = root.find(f"{rcn.NS_WFS}member")
    root.remove(member)
    root.set("numberReturned", str(rows))
    root.set("numberMatched", str(total))
    if next_page:
        root.set("next", "https://example.test/next")
    for i in range(rows):
        copy = ET.fromstring(ET.tostring(member))
        copy[0].set("{http://www.opengis.net/gml/3.2}id", str(ident + i))
        if uppercase:
            for child in copy[0]:
                child.tag = rcn.NS_MS + child.tag.rsplit("}", 1)[-1].upper()
                if child.tag.endswith("TRAN_RODZAJ_RYNKU"):
                    child.text = "rynekWtorny"
        root.append(copy)
    return ET.tostring(root)


@pytest.mark.parametrize("value,expected", [
    ("pierwotny", "p"), ("wtórny", "w"), ("rynekPierwotny", "p"),
    ("rynekWtorny", "w"), (None, None), ("", None),
])
def test_market_vocabularies(value, expected):
    row = next(rcn._parse_members(_page(uppercase=True), "lokale"))
    row["tran_rodzaj_rynku"] = value
    assert rcn._compact_lok(row)["rynek"] == expected
    building = dict(row, bud_adres="MSC:Gliwice;UL:Polna;NR_PORZ:1")
    assert rcn._compact_bud(building)["rynek"] == expected


def test_unknown_market_fails_closed():
    with pytest.raises(ValueError, match="unknown market"):
        rcn._market("newUnsupportedEnum")


@pytest.mark.parametrize("page", [
    b"<html />", b"<ExceptionReport />", b"<broken",
    _page().replace(b'numberReturned="1"', b'numberReturned="2"'),
    _page().replace(b"lokale", b"unexpected"),
])
def test_invalid_wfs_pages_are_not_empty_evidence(page):
    with pytest.raises(Exception):
        list(rcn._parse_members(page, "lokale"))


def _fetch_pages(monkeypatch, pages, totals=(None, None)):
    totals = iter(totals)
    monkeypatch.setattr(rcn, "_get_total", lambda *a: next(totals))
    starts = []
    pages = iter(pages)
    def get_page(*args):
        starts.append(args[-1])
        return next(pages)
    monkeypatch.setattr(rcn, "_get_page", get_page)
    rows = rcn.fetch(None, "ms:lokale", "", rcn.LOK_PROPS, "lokale",
                     rcn._compact_lok, log=lambda *a: None)
    return rows, starts


def test_short_pages_without_next_links_are_not_eof(monkeypatch):
    rows, starts = _fetch_pages(monkeypatch, [
        _page(2), _page(1, ident=3, uppercase=True), _page(0, total=3),
    ])
    # Per-page duplicates collapse; identical deeds on different pages survive.
    assert len(rows) == 2
    assert starts == [0, 2, 3]
    assert all(row["rynek"] == "w" for row in rows)


def test_known_total_can_appear_after_unknown_total(monkeypatch):
    rows, starts = _fetch_pages(monkeypatch, [_page(), _page(total=2, ident=2)])
    assert len(rows) == 2 and starts == [0, 1]


@pytest.mark.parametrize("pages,reason", [
    ([_page(), _page()], "repeated page"),
    ([_page(total=3), _page(0, total=3)], "premature empty"),
    ([_page(total=3), _page(total=4, ident=2)], "inconsistent total"),
    ([_page(total=1, next_page=True)], "next link beyond"),
    ([_page(0, next_page=True)], "premature empty"),
    ([_page(0)], "no usable transactions"),
    ([_page().replace(b"dok_data", b"unknown_date")], "missing expected fields"),
])
def test_incomplete_or_changed_pages_fail_closed(monkeypatch, pages, reason):
    with pytest.raises(ValueError, match=reason):
        _fetch_pages(monkeypatch, pages)


def _snapshot(n=10, fetched="2026-09-17"):
    return {"fetched": fetched, "lokale": [_tx(msc="Gliwice" if i == 0 else f"Town{i}") for i in range(n)],
            "budynki": [_tx()] * n}


@pytest.mark.parametrize("failure", ["empty", "shrunk", "interrupted", "save"])
def test_failed_refresh_preserves_cache_bytes_and_reports_degraded(tmp_path, monkeypatch, failure):
    path = tmp_path / "rcn.json.gz"
    previous = _snapshot()
    rcn.save_snapshot(path, previous)
    original = path.read_bytes()
    def fetch(*args, **kwargs):
        if failure == "interrupted":
            raise OSError("second layer interrupted")
        if failure == "empty":
            return [], []
        return [_tx()] * (7 if failure == "shrunk" else 11), [_tx()] * 11
    monkeypatch.setattr(rcn, "fetch_all", fetch)
    if failure == "save":
        def fail_save(*args):
            raise OSError("disk full")
        monkeypatch.setattr(rcn, "save_snapshot", fail_save)
    assert rcn.refresh(path, None, today="2026-09-26") == previous
    assert path.read_bytes() == original
    assert rcn.refresh.last_health["status"] == "degraded"
    assert rcn.refresh.last_health["error"]
    rec = _rec()
    rcn.match([rec], previous, log=lambda *a: None)
    assert rec["sales"]


def test_recent_poisoned_cache_recovers_before_failed_refresh(tmp_path, monkeypatch):
    path = tmp_path / "rcn.json.gz"
    rcn.save_snapshot(path, {"fetched": "2026-09-26", "lokale": [], "budynki": []})
    baseline = _snapshot()
    monkeypatch.setattr(rcn, "recover_snapshot", lambda *a, **k: baseline)
    monkeypatch.setattr(rcn, "fetch_all", lambda *a, **k: ([], []))
    assert rcn.refresh(path, None, today="2026-09-26") == baseline
    assert rcn.load_snapshot(path) == baseline
    assert rcn.refresh.last_health["status"] == "degraded"
    assert rcn.refresh.last_health["recovered_from"] == rcn.RECOVERY["24"]["ref"]


def test_healthy_cache_skips_network_and_other_region_does_not_use_recovery(tmp_path, monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail("unexpected network call")
    monkeypatch.setattr(rcn, "fetch_all", unexpected)
    monkeypatch.setattr(rcn, "recover_snapshot", unexpected)
    path = tmp_path / "cache.gz"
    rcn.save_snapshot(path, _snapshot(fetched="2026-09-26"))
    assert rcn.refresh(path, None, teryt_prefix="16", today="2026-09-26")
    assert rcn.refresh.last_health["status"] == "healthy"
    monkeypatch.setattr(rcn, "fetch_all", lambda *a, **k: ([], []))
    assert rcn.refresh(tmp_path / "missing.gz", None, teryt_prefix="16", today="2026-09-26") is None
    assert rcn.refresh.last_health["status"] == "unavailable"


def test_recovery_checksum_is_required(monkeypatch):
    class Session:
        def get(self, *args, **kwargs):
            return self
        def raise_for_status(self):
            pass
        content = b"not the audited snapshot"
    with pytest.raises(ValueError, match="checksum"):
        rcn.recover_snapshot(Session(), "24")


def test_successful_refresh_replaces_cache_atomically(tmp_path, monkeypatch):
    path = tmp_path / "cache.gz"
    previous = _snapshot()
    rcn.save_snapshot(path, previous)
    monkeypatch.setattr(rcn, "fetch_all", lambda *a, **k: ([_tx()] * 12, [_tx()] * 11))
    candidate = rcn.refresh(path, None, today="2026-09-26")
    assert candidate == rcn.load_snapshot(path)
    assert candidate["fetched"] == "2026-09-26"
    assert rcn.refresh.last_health == {
        "status": "healthy", "fetched": "2026-09-26",
        "counts": {"lokale": 12, "budynki": 11}, "error": None,
    }


def test_hits_total_verifies_terminal_page_without_empty_request(monkeypatch):
    rows, starts = _fetch_pages(monkeypatch, [_page(), _page(ident=2)], totals=(2, 2))
    assert len(rows) == 2 and starts == [0, 1]


def test_hits_total_change_rejects_completed_pull(monkeypatch):
    with pytest.raises(ValueError, match="final total"):
        _fetch_pages(monkeypatch, [_page()], totals=(1, 2))


@pytest.mark.parametrize("response,expected", [
    (_page(0, total=123), 123), (_page(0), None),
])
def test_hits_response_parsing(response, expected):
    class Session:
        def get(self, url, **kwargs):
            assert 'resultType=hits' in url
            self.content = response
            return self
        def raise_for_status(self):
            pass
    assert rcn._get_total(Session(), 'ms:lokale', '') == expected


@pytest.mark.parametrize("response", [b'<html/>', _page(1), _page(0, total=-1)])
def test_hits_rejects_invalid_responses(response):
    class Session:
        content = response
        def get(self, *args, **kwargs): return self
        def raise_for_status(self): pass
    with pytest.raises(ValueError):
        rcn._get_total(Session(), 'ms:lokale', '')


def test_building_cache_allows_zero_area_as_unreported():
    snapshot = _snapshot(1)
    snapshot['budynki'][0]['a'] = 0
    rcn.validate_snapshot(snapshot)
    snapshot['lokale'][0]['a'] = 0
    with pytest.raises(ValueError, match='area'):
        rcn.validate_snapshot(snapshot)


def test_no_recovery_and_small_fresh_pull_cannot_bypass_known_baseline(tmp_path, monkeypatch):
    def unavailable(*args, **kwargs): raise OSError('no recovery download')
    monkeypatch.setattr(rcn, 'recover_snapshot', unavailable)
    monkeypatch.setattr(rcn, 'fetch_all', lambda *a, **k: ([_tx()], [_tx()]))
    path = tmp_path / 'cache.gz'
    assert rcn.refresh(path, None, today='2026-09-26') is None
    assert not path.exists()
    assert rcn.refresh.last_health['status'] == 'unavailable'
