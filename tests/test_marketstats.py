"""marketstats: weekly/monthly series, DOM histogram, cut share. Offline."""
from scraper import marketstats

TODAY = "2026-07-07"


def test_week_of():
    assert marketstats._week_of("2026-07-07") == "2026-07-06"   # Tue -> Mon
    assert marketstats._week_of("2026-07-06") == "2026-07-06"
    assert marketstats._week_of("") is None


def test_axis_months():
    ms = marketstats._axis("2025-11", "2026-02", "month")
    assert ms == ["2025-11", "2025-12", "2026-01", "2026-02"]


def _rec(typ="flat", area=50.0, town="Gliwice", first="2026-06-15", obs=None, **extra):
    r = {"type": typ, "area": area, "first_seen": first,
         "snapshot": {"locality": town},
         "observations": obs or [{"date": first, "price": 400000, "url": "u1"}]}
    r.update(extra)
    return r


def test_weekly_series():
    recs = [
        _rec(obs=[{"date": "2026-06-15", "price": 400000, "url": "u1"},
                  {"date": "2026-06-22", "price": 380000, "url": "u1"}]),
        _rec(typ="house", area=100.0, first="2026-06-16",
             delisted="2026-06-24",
             obs=[{"date": "2026-06-16", "price": 500000, "url": "u2"}]),
        _rec(development=True),   # excluded everywhere
    ]
    w = marketstats._weekly(recs, {"gliwice": "Gliwice"})
    assert w["weeks"] == ["2026-06-15", "2026-06-22"]
    f = w["global"]["flat"]
    assert f["active"] == [1, 1]
    assert f["med"] == [8000, 7600]          # 400k/50 then 380k/50
    assert f["new"] == [1, 0]
    assert f["cuts"] == [0, 1]
    h = w["global"]["house"]
    assert h["new"] == [1, 0] and h["gone"] == [0, 1]
    g = w["towns"]["Gliwice"]
    assert g["flat"]["med"] == [8000, 7600]
    assert g["house"]["active"] == [1, 0]


def test_rcn_monthly_min_n_and_town():
    lok = ([{"d": "2025-05-10", "c": 9000 * 50, "a": 50.0, "rynek": "w", "msc": "Gliwice"}] * 5
           + [{"d": "2025-06-10", "c": 8000 * 50, "a": 50.0, "rynek": "w", "msc": "Gliwice"}] * 2
           + [{"d": "2025-05-11", "c": 12000 * 50, "a": 50.0, "rynek": "p", "msc": "Gliwice"}] * 5)
    r = marketstats._rcn_monthly({"lokale": lok}, {"gliwice": "Gliwice"}, "2025-06")
    i5 = r["months"].index("2025-05")
    i6 = r["months"].index("2025-06")
    assert r["global"]["w"]["med"][i5] == 9000
    assert r["global"]["w"]["med"][i6] is None          # n=2 < MIN_MONTH_N
    assert r["global"]["w"]["n"][i6] == 2
    assert r["global"]["p"]["med"][i5] == 12000
    assert r["towns"]["Gliwice"]["w"]["med"][i5] == 9000
    assert "p" not in r["towns"]["Gliwice"]             # per-town is wtorny-only


def test_dom_and_cut_share():
    recs = [
        _rec(delisted="2026-06-25", first="2026-06-15"),                 # 10 days
        _rec(delisted="2026-06-30", first="2026-01-01"),                 # 180 days
        _rec(obs=[{"date": "2026-06-15", "price": 400000, "url": "u1"},
                  {"date": "2026-06-16", "price": 390000, "url": "u1"}]),  # cut
        _rec(obs=[{"date": "2026-06-15", "price": 400000, "url": "u1"},
                  {"date": "2026-06-16", "price": 400000, "url": "u1"}]),  # no cut
    ]
    dom, share = marketstats._dom_and_cuts(recs)
    assert dom["counts"][0] == 1                     # <=30
    assert dom["counts"][3] == 1                     # 91-180
    assert share["flat"] == 0.5                      # 4 recs, 2 with >=2 prices...

    # only the two multi-observation records enter the base
    assert share["house"] is None


def test_build_smoke():
    out = marketstats.build([_rec()], {"lokale": []}, today=TODAY)
    assert out["built"] == TODAY
    assert out["weekly"]["weeks"] == ["2026-06-15"]
    assert out["rcn"]["months"] == []
