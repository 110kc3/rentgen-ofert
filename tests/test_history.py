"""History lifecycle: url-fallback matching, archived ingestion, delist sweep,
timeline and archive building. Offline — no network."""
from scraper import delist, history


H1, H2 = 3, 5           # hamming(3,5)=1 -> same photos (threshold 40)
FAR = (1 << 64) - 1     # 64 bits differ from H1 -> different photos (>40)


def _prop(**kw):
    base = dict(type="flat", area=50.0, url="https://otodom.pl/a1", price=300000,
                source="otodom", phashes=[H1], photo_urls=["img1.jpg"],
                title="Mieszkanie", locality="Gliwice", street="Asnyka",
                rooms=2, floor=1, offers=[])
    base.update(kw)
    return base


def test_photo_match_appends_observation_and_snapshot():
    records = []
    history.update([_prop()], records, "2026-06-01")
    history.update([_prop(url="https://olx.pl/b2", phashes=[H2], price=290000,
                          source="olx")], records, "2026-06-05")
    assert len(records) == 1
    rec = records[0]
    assert [o["url"] for o in rec["observations"]] == ["https://otodom.pl/a1", "https://olx.pl/b2"]
    assert rec["last_seen"] == "2026-06-05"
    assert rec["snapshot"]["street"] == "Asnyka"
    assert rec["photo_urls"] == ["img1.jpg"]


def test_url_fallback_prevents_record_bloat_for_photoless_listings():
    records = []
    p = _prop(phashes=[], photo_urls=[])
    history.update([dict(p)], records, "2026-06-01")
    history.update([dict(p)], records, "2026-06-02")
    assert len(records) == 1          # was: one fresh record per run


def test_different_photos_same_url_do_not_merge():
    records = []
    history.update([_prop()], records, "2026-06-01")
    # same URL recycled for a different flat (different photos) -> new record
    history.update([_prop(phashes=[FAR], area=50.0)], records, "2026-06-02")
    assert len(records) == 2


def test_observe_archived_marks_delisted():
    records = []
    history.update([_prop(source="nieruchomosci-online",
                          url="https://x.nieruchomosci-online.pl/1.html")],
                   records, "2026-06-01")
    archived = [_prop(source="nieruchomosci-online",
                      url="https://x.nieruchomosci-online.pl/1.html",
                      archived=True)]
    n = history.observe_archived(archived, records, "2026-06-10")
    assert n == 1
    assert records[0]["delisted"] == "2026-06-10"
    statuses = [o.get("status") for o in records[0]["observations"]]
    assert "archived" in statuses


def test_relist_clears_delisted():
    records = []
    history.update([_prop()], records, "2026-06-01")
    records[0]["delisted"] = "2026-06-05"
    history.update([_prop(url="https://otodom.pl/new", phashes=[H2])],
                   records, "2026-06-20")
    assert "delisted" not in records[0]
    assert len(records) == 1


def test_timeline_orders_and_labels_events():
    rec = {
        "type": "flat", "area": 50.0, "first_seen": "2026-06-01",
        "delisted": "2026-06-20",
        "observations": [
            {"date": "2026-06-01", "price": 300000, "url": "u1", "source": "otodom"},
            {"date": "2026-06-05", "price": 290000, "url": "u1", "source": "otodom"},
            {"date": "2026-06-08", "price": 290000, "url": "u2", "source": "olx"},
        ],
        "sales": [
            {"date": "2021-03-01", "price": 200000, "kind": "past", "confidence": "wysoka"},
            {"date": "2026-08-01", "price": 285000, "kind": "sold", "confidence": "wysoka"},
        ],
    }
    kinds = [e["kind"] for e in history.timeline(rec)]
    assert kinds == ["sale_past", "listed", "price", "relist", "delisted", "sale"]


def test_build_archive_only_delisted():
    records = [
        {"type": "flat", "area": 50.0, "first_seen": "2026-06-01",
         "observations": [{"date": "2026-06-01", "price": 300000, "url": "u1", "source": "otodom"}],
         "snapshot": {"title": "M3", "locality": "Gliwice"}},
        {"type": "flat", "area": 60.0, "first_seen": "2026-06-01", "delisted": "2026-06-15",
         "observations": [{"date": "2026-06-01", "price": 400000, "url": "u2", "source": "olx"}],
         "snapshot": {"title": "M4", "locality": "Zabrze"},
         "sales": [{"date": "2026-07-01", "price": 395000, "kind": "sold", "confidence": "średnia"}]},
    ]
    arch = history.build_archive(records)
    assert len(arch) == 1
    assert arch[0]["title"] == "M4"
    assert arch[0]["sold"]["price"] == 395000
    assert arch[0]["price"] == 400000


class _FakeResp:
    def __init__(self, status=200, text="", url="", history=()):
        self.status_code, self.text, self.url, self.history = status, text, url, list(history)


class _FakeSession:
    def __init__(self, resp):
        self.resp = resp

    def get(self, url, **kw):
        return self.resp


def test_delist_sweep_confirms_404():
    records = []
    history.update([_prop()], records, "2026-06-01")
    n = delist.sweep(records, "2026-06-20", _FakeSession(_FakeResp(status=404)),
                     active_urls=set(), log=lambda *a: None)
    assert n == 1
    assert records[0]["delisted"] == "2026-06-01"


def test_delist_sweep_respects_grace_and_live_pages():
    records = []
    history.update([_prop()], records, "2026-06-01")
    live = _FakeSession(_FakeResp(status=200, text="<h1>Mieszkanie na sprzedaż</h1>"))
    # within grace period -> not even checked
    assert delist.sweep(records, "2026-06-03", live, log=lambda *a: None) == 0
    # stale but page still live -> not delisted
    assert delist.sweep(records, "2026-06-20", live, log=lambda *a: None) == 0
    assert "delisted" not in records[0]


def test_delist_gone_markers():
    sess = _FakeSession(_FakeResp(status=200, text="To ogłoszenie jest nieaktualne"))
    assert delist.is_gone("https://otodom.pl/x", sess) is True
    sess2 = _FakeSession(_FakeResp(status=200, text='"availability":"https://schema.org/OutOfStock"'))
    assert delist.is_gone("https://x.nieruchomosci-online.pl/1.html", sess2) is True


def test_compact_merges_photoless_duplicates():
    records = [
        {"type": "flat", "area": 50.0, "hashes": [H1], "first_seen": "2026-06-01",
         "observations": [{"date": "2026-06-01", "price": 300000, "url": "u1", "source": "otodom"}],
         "snapshot": {"locality": "Gliwice"}},
        {"type": "flat", "area": 50.0, "hashes": [], "first_seen": "2026-06-02",
         "observations": [{"date": "2026-06-02", "price": 295000, "url": "u1", "source": "otodom"}]},
        {"type": "flat", "area": 50.0, "hashes": [], "first_seen": "2026-06-03",
         "observations": [{"date": "2026-06-03", "price": 295000, "url": "u1", "source": "otodom"}]},
    ]
    out = history.compact(records)
    assert len(out) == 1
    keep = out[0]
    assert keep["hashes"] == [H1]                       # merged into the hashed one
    assert [o["date"] for o in keep["observations"]] == ["2026-06-01", "2026-06-02", "2026-06-03"]
    assert keep["first_seen"] == "2026-06-01"
    assert keep["last_seen"] == "2026-06-03"


def test_compact_keeps_conflicting_photo_records_apart():
    records = [
        {"type": "flat", "area": 50.0, "hashes": [H1], "first_seen": "2026-06-01",
         "observations": [{"date": "2026-06-01", "url": "u1", "price": 1, "source": "olx"}]},
        {"type": "flat", "area": 50.0, "hashes": [FAR], "first_seen": "2026-06-02",
         "observations": [{"date": "2026-06-02", "url": "u1", "price": 2, "source": "olx"}]},
    ]
    assert len(history.compact(records)) == 2


def test_development_records_skip_relist_delist_rcn_archive():
    from scraper import rcn
    records = []
    dev = _prop(development=True, title="Apartamenty Nowe — etap I")
    history.update([dict(dev)], records, "2026-06-01")
    rec = records[0]
    assert rec["development"] is True
    # same photos under a new URL would normally flag a relist — not for devs
    p2 = dict(dev, url="https://otodom.pl/other-unit")
    history.update([p2], records, "2026-06-10")
    assert p2["relisted"] is False
    # delist sweep ignores dev records entirely
    n = delist.sweep(records, "2026-06-30", _FakeSession(_FakeResp(status=404)),
                     active_urls=set(), log=lambda *a: None)
    assert n == 0
    # rcn.match skips dev records
    snap = {"lokale": [{"d": "2021-01-01", "c": 300000, "a": 50.0, "izb": 2,
                        "kond": 2, "rynek": "w", "msc": "Gliwice",
                        "ul": "Asnyka", "nr": "1"}], "budynki": []}
    assert rcn.match(records, snap, log=lambda *a: None) == 0
    # and archive excludes them even if delisted
    rec["delisted"] = "2026-06-30"
    assert history.build_archive(records) == []


def test_overrides_pin_and_apply(tmp_path):
    from scraper import overrides
    path = tmp_path / "overrides.json"
    overrides.pin("https://otodom.pl/a1", path=path,
                  street="Adama Asnyka", nr="11", floor=3, bogus="dropped")
    records = []
    history.update([_prop()], records, "2026-06-01")
    n = overrides.apply(records, overrides.load(path), log=lambda *a: None)
    assert n == 1
    snap = records[0]["snapshot"]
    assert snap["street"] == "Adama Asnyka" and snap["nr"] == "11" and snap["floor"] == 3
    assert "bogus" not in snap
    assert records[0]["manual"] is True
    # unknown URL -> ignored quietly
    assert overrides.apply(records, {"https://x/unknown": {"nr": "5"}},
                           log=lambda *a: None) == 0
