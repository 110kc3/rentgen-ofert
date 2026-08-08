"""rcnstats: deed zl/m2 benchmarks + ask-vs-sold gap. Offline."""
from scraper import rcnstats

TODAY = "2026-07-07"


def _lok(d, c, a, rynek="w", msc="Gliwice"):
    return {"d": d, "c": c, "a": a, "rynek": rynek, "msc": msc}


def test_bucket_of():
    assert rcnstats.bucket_of("flat", 39.9) == "<40"
    assert rcnstats.bucket_of("flat", 40) == "40-59"
    assert rcnstats.bucket_of("flat", 59.9) == "40-59"
    assert rcnstats.bucket_of("flat", 130) == "120+"
    assert rcnstats.bucket_of("house", 99) == "<100"
    assert rcnstats.bucket_of("house", 250) == "220+"
    assert rcnstats.bucket_of("flat", None) is None
    assert rcnstats.bucket_of("plot", 500) is None


def test_bucket_benchmarks_median_and_window():
    # five recent deeds at 8000..12000 zl/m2 for 50 m2 flats
    lokale = [_lok("2025-0%d-01" % (i + 1), (8000 + i * 1000) * 50, 50.0)
              for i in range(5)]
    # too old -> excluded; absurd zl/m2 -> excluded; other bucket -> own (thin) group
    lokale += [_lok("2019-01-01", 99000 * 50, 50.0),
               _lok("2025-06-01", 100, 50.0),
               _lok("2025-06-01", 9000 * 30, 30.0)]
    out = rcnstats.build({"lokale": lokale}, [], today=TODAY)
    b = out["towns"]["gliwice"]["flat"]["40-59"]["w"]
    assert b["n"] == 5
    assert b["med"] == 10000 * 50 / 50  # median of 8..12k
    assert b["p25"] == 9000 and b["p75"] == 11000
    assert "<40" not in out["towns"]["gliwice"]["flat"]  # below MIN_N -> dropped
    assert out["towns"]["gliwice"]["name"] == "Gliwice"


def test_markets_kept_apart():
    lokale = ([_lok("2025-05-01", 9000 * 50, 50.0, rynek="w") for _ in range(5)]
              + [_lok("2025-05-01", 12000 * 50, 50.0, rynek="p") for _ in range(5)])
    out = rcnstats.build({"lokale": lokale}, [], today=TODAY)
    b = out["towns"]["gliwice"]["flat"]["40-59"]
    assert b["w"]["med"] == 9000
    assert b["p"]["med"] == 12000


def _sold_record(ask=400000, deed=376000, first="2026-01-01", gone="2026-04-01",
                 **extra):
    rec = {"type": "flat", "area": 50.0, "first_seen": first, "delisted": gone,
           "observations": [{"date": first, "price": ask, "url": "u1"},
                            {"date": "2026-03-01", "price": ask, "url": "u1"}],
           "snapshot": {"locality": "Gliwice"},
           "sales": [{"kind": "sold", "date": "2026-05-01", "price": deed}]}
    rec.update(extra)
    return rec


def test_gap_pairs():
    pairs = list(rcnstats.gap_pairs([_sold_record()]))
    assert len(pairs) == 1
    town, disp, typ, pct, days = pairs[0]
    assert (town, disp, typ) == ("gliwice", "Gliwice", "flat")
    assert round(pct, 1) == -6.0          # 376k on a 400k ask
    assert days == 90


def test_gap_pairs_skips_noise():
    # developments, still-listed, deed-less, absurd gaps and udzial asks
    assert not list(rcnstats.gap_pairs([_sold_record(development=True)]))
    assert not list(rcnstats.gap_pairs([_sold_record(delisted=None)]))
    assert not list(rcnstats.gap_pairs([_sold_record(sales=[])]))
    assert not list(rcnstats.gap_pairs([_sold_record(deed=100000)]))   # -75%
    assert not list(rcnstats.gap_pairs([_sold_record(ask=5000)]))


def test_build_gap_summaries():
    recs = [_sold_record() for _ in range(5)]
    out = rcnstats.build({}, recs, today=TODAY)
    g = out["towns"]["gliwice"]["gap"]
    assert g["n"] == 5 and g["med_pct"] == -6.0 and g["med_days"] == 90
    assert out["gap"]["all"]["n"] == 5
    assert out["gap"]["flat"]["med_pct"] == -6.0
    assert "house" not in out["gap"]


# --- register freshness ------------------------------------------------------
# A powiat that stops reporting can confirm no recent sale at all, so the town's
# newest deed date is published and the laggards are listed. (Real case: Gliwice
# was 5 months behind its neighbours in 2026-08 — see _freshness.)

def _town(msc, last, n=rcnstats.STALE_MIN_DEEDS):
    """n deeds for `msc`, all dated `last` (enough of them to be benchmarked)."""
    return [_lok(last, 9000 * 50, 50.0, msc=msc) for _ in range(n)]


def test_freshness_lag_per_town():
    snap = {"lokale": _town("Gliwice", "2026-02-25") + _town("Katowice", "2026-07-01")}
    fresh = rcnstats._freshness(snap, TODAY)
    assert fresh["gliwice"]["last"] == "2026-02-25"
    assert fresh["gliwice"]["lag"] == 132          # 2026-02-25 -> 2026-07-07
    assert fresh["katowice"]["lag"] == 6
    assert fresh["gliwice"]["name"] == "Gliwice"


def test_freshness_spans_both_layers():
    snap = {"lokale": _town("Gliwice", "2026-01-01", n=1),
            "budynki": _town("Gliwice", "2026-06-01", n=1)}
    assert rcnstats._freshness(snap, TODAY)["gliwice"]["last"] == "2026-06-01"


def test_build_flags_stale_towns():
    snap = {"lokale": _town("Gliwice", "2026-02-25") + _town("Katowice", "2026-07-01")}
    out = rcnstats.build(snap, [], today=TODAY)
    assert out["stale_days"] == rcnstats.STALE_DAYS
    assert [s["name"] for s in out["stale"]] == ["Gliwice"]   # Katowice is current
    assert out["stale"][0]["lag"] == 132
    # a town the dashboard can look up keeps its own freshness stamp, stale or not
    assert out["towns"]["gliwice"]["deeds"] == {"last": "2026-02-25", "lag": 132}
    assert out["towns"]["katowice"]["deeds"]["lag"] == 6


def test_stale_town_listed_even_without_benchmarks():
    """`towns` only holds towns with publishable benchmarks, so the standalone
    `stale` list is what the empty-state explanation has to read."""
    snap = {"lokale": _town("Lubliniec", "2019-01-01")}      # far outside the window
    out = rcnstats.build(snap, [], today=TODAY)
    assert "lubliniec" not in out["towns"]
    assert [s["name"] for s in out["stale"]] == ["Lubliniec"]


def test_stale_ignores_thin_towns():
    """A hamlet with three deeds ever is not a reporting failure worth naming."""
    snap = {"lokale": _town("Pyskowice", "2020-01-01", n=3)}
    assert rcnstats.build(snap, [], today=TODAY)["stale"] == []
