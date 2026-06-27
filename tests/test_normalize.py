from scraper.normalize import (
    otodom_rooms, olx_rooms, to_float, to_int, dedupe,
)


def test_room_maps():
    assert otodom_rooms("SEVEN") == 7
    assert otodom_rooms("one") == 1
    assert otodom_rooms(None) is None
    assert otodom_rooms("MORE") is None
    assert olx_rooms("three") == 3
    assert olx_rooms("3") == 3
    assert olx_rooms("studio") is None


def test_number_coercion():
    assert to_float("268,87") == 268.87
    assert to_float("1 124") == 1124.0
    assert to_float("3\xa0644,88") == 3644.88
    assert to_float(None) is None
    assert to_int("3 644,88") == 3645
    assert to_int("nonsense") is None


def _l(**kw):
    base = dict(source="otodom", source_id="1", url="u1", title="t", type="flat",
                price=None, area=None, price_per_m2=None, rooms=None, plot_area=None,
                floor=None, district=None, street=None, is_private=None, agency=None,
                image=None, created=None)
    base.update(kw)
    return base


def test_dedupe_merges_cross_portal_same_price():
    # same flat on two portals at the same asking price (small rounding diff ok)
    a = _l(source="otodom", url="oto", price=900000, area=120.0, rooms=5,
           district="Sośnica", image="x", plot_area=600, created="2026-06-10")
    b = _l(source="gratka", url="gra", price=900400, area=120.0, rooms=5,
           district="sośnica", created="2026-06-12")          # same 1k bucket, case-diff
    out = dedupe([a, b])
    assert len(out) == 1
    p = out[0]
    assert p["sources"] == ["otodom", "gratka"]               # otodom ranked first
    assert p["price"] == 900000 and p["price_max"] == 900400  # range across offers
    assert len(p["offers"]) == 2
    assert p["created"] == "2026-06-12"                        # most recent across offers
    assert p["plot_area"] == 600                              # filled from the offer that had it


def test_dedupe_keeps_distinct_and_unmatchable():
    a = _l(source="otodom", url="o", price=500000, area=50.0, rooms=2, district="Trynek")
    b = _l(source="olx", url="x", price=640000, area=70.0, rooms=3, district="Trynek")
    c = _l(source="olx", url="x2", price=None, area=None)      # no area -> unmatchable
    out = dedupe([a, b, c])
    assert len(out) == 3
    assert all(len(p["offers"]) == 1 for p in out)


def test_dedupe_price_only_match_when_rooms_missing():
    # same type+area+exact price, rooms missing on both -> still merged
    a = _l(source="otodom", url="o", price=430000, area=51.0)
    b = _l(source="olx", url="x", price=430000, area=51.0)
    out = dedupe([a, b])
    assert len(out) == 1 and len(out[0]["offers"]) == 2


def test_dedupe_merges_same_size_at_different_prices():
    # same flat, two portals, different price -> one card, cheapest highlighted
    a = _l(source="otodom", url="o", price=480000, area=50.0, rooms=2)
    b = _l(source="olx", url="x", price=520000, area=50.0, rooms=2)
    out = dedupe([a, b])
    assert len(out) == 1
    p = out[0]
    assert p["price"] == 480000 and p["price_max"] == 520000
    assert p["cheapest"]["price"] == 480000 and p["cheapest"]["source"] == "otodom"


def test_dedupe_splits_on_huge_price_gap():
    # a 0.8M and a 1.8M "220 m2" house are never the same house -> stay separate
    a = _l(source="otodom", url="o", price=800000, area=220.0, rooms=5)
    b = _l(source="olx", url="x", price=1800000, area=220.0, rooms=5)
    out = dedupe([a, b])
    assert len(out) == 2


def test_same_photos_threshold():
    from scraper.normalize import same_photos
    assert same_photos([0b0], [0b0]) is True              # identical hash
    assert same_photos([0], [(1 << 40) - 1]) is True      # hamming 40 == threshold
    assert same_photos([0], [(1 << 41) - 1]) is False     # hamming 41 > threshold
    assert same_photos([], [123]) is False                # no photos -> no match


def test_dedupe_photo_match_overrides_price():
    # same size + matching galleries -> merge even at very different prices
    a = _l(source="otodom", url="o", price=400000, area=55.0, rooms=2)
    b = _l(source="olx", url="x", price=560000, area=55.0, rooms=2)
    a["phashes"], b["phashes"] = [123456789], [123456789]   # identical photo
    out = dedupe([a, b])
    assert len(out) == 1 and out[0]["price"] == 400000 and out[0]["price_max"] == 560000


def test_dedupe_photo_mismatch_keeps_separate():
    # same size, same price, but different galleries -> two properties
    a = _l(source="otodom", url="o", price=500000, area=55.0, rooms=2)
    b = _l(source="olx", url="x", price=500000, area=55.0, rooms=2)
    a["phashes"], b["phashes"] = [0], [(1 << 63) - 1]       # ~63 apart, far > 40
    out = dedupe([a, b])
    assert len(out) == 2


def test_dedupe_merges_when_rooms_missing_on_one_side():
    # houses ignore rooms (OLX omits them); same area+price still merges
    a = _l(source="otodom", url="o", type="house", price=990000, area=150.0, rooms=5)
    b = _l(source="olx", url="x", type="house", price=990000, area=150.0, rooms=None)
    out = dedupe([a, b])
    assert len(out) == 1 and len(out[0]["offers"]) == 2
