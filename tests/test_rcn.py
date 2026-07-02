"""RCN: GML parsing, compaction, street matching and sale attachment. Offline."""
from scraper import rcn

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
