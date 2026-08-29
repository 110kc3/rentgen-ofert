"""gratka/morizon gallery extraction, pinned to real detail pages.

The fixtures are trimmed from live pages for the SAME ad (gratka 48557359 /
morizon mzn2047889133, fetched 2026-08-09), kept because this extractor has now
broken twice by way of a host rename and each time it failed silently: morizon
returned zero hashes for every one of its 9 505 listings in the 2026-08-08 run,
so it merged with nothing and shipped ~7 000 duplicate cards. A host list is not
a specification; a real page is.

The two fixtures also *prove* the thing the merge key rests on — both portals
serve byte-identical `d-gr.cdngr.pl` origins carrying gratka's ad id.
"""
import pathlib

from scraper import cache, net, normalize, photomatch

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def _html(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_both_portals_extract_the_same_three_photos():
    gr = photomatch._EXTRACTORS["gratka"](_html("gratka_detail.html"))
    mz = photomatch._EXTRACTORS["morizon"](_html("morizon_detail.html"))
    # the page shows one photo in five renditions before the second one starts,
    # so a naive first-five slice hashed a single photo five times
    assert len(gr) == 3 and len(mz) == 3
    assert {photomatch.gratka_ad_id(u) for u in gr} == {"48557359"}
    assert {photomatch.gratka_ad_id(u) for u in mz} == {"48557359"}


def test_blog_teasers_on_the_same_cdn_are_not_gallery_photos():
    """Both portals' article thumbnails ride the same `/thumb/<base64>/` path
    AND end in `.jpg`, so a host-only pattern quietly hashes stock article art
    as if it were the property."""
    for name in ("gratka_detail.html", "morizon_detail.html"):
        html = _html(name)
        # the decoy is only visible once decoded — which is the whole point
        all_thumbs = [m.group(0) for m in photomatch._CDN_THUMB.finditer(html)]
        decoded = [photomatch._decode_origin(m.group(1))
                   for m in photomatch._CDN_THUMB.finditer(html)]
        assert any("blog/wp-content" in (d or "") for d in decoded), \
            "fixture must keep the decoys"
        urls = photomatch._cdn_gallery(html)
        assert urls and len(urls) < len(all_thumbs)
        assert all("blog/wp-content" not in (photomatch._decode_origin(
            u.split("/thumb/")[1].split("/")[0]) or "") for u in urls)


def test_morizon_host_rename_is_covered():
    """The break that started it: galleries moved to img*.staticmorizon.com.pl."""
    assert all("staticmorizon.com.pl" in u
               for u in photomatch._EXTRACTORS["morizon"](_html("morizon_detail.html")))


def test_gratka_ad_id_ignores_anything_that_is_not_an_ad_photo():
    # `gr-col` is a different id space (agency collections), not an ad id
    col = ("https://img1.staticmorizon.com.pl/thumb/"
           "aHR0cHM6Ly9kLWdyLmNkbmdyLnBsL2thZHJ5L2svci9nci1jb2wvMWUvNGYvMzk0NDVfMTM5MzQwNTk3NS5qcGc="
           "/3x2_s:fill_and_crop/x.jpg")
    assert photomatch.gratka_ad_id(col) is None
    assert photomatch.gratka_ad_id("https://example.com/photo.jpg") is None
    assert photomatch.gratka_ad_id("") is None
    assert photomatch.gratka_ad_id(None) is None
    # unpadded base64 must still decode
    assert photomatch.gratka_ad_id(
        "https://thumbs.cdngr.pl/thumb/"
        "aHR0cHM6Ly9kLWdyLmNkbmdyLnBsL2thZHJ5L2svci9nci1vZ2wvMWUvMGYvNDg1NTczNTlfMTU0NjcwMDM4NS5qcGc"
        "/3x2_l/x.jpg") == "48557359"


# ---- the budget, and not lying to the cache about it ------------------------

class _Sess:
    """Counts detail-page fetches; every gallery comes back empty."""
    def __init__(self):
        self.calls = 0

    def get(self, url, **kw):
        self.calls += 1
        raise RuntimeError("no photos here")


def test_a_photoless_ad_stops_being_refetched_every_run():
    """morizon's 9 505 detail pages were re-fetched every run, always returned
    nothing, and were charged to the photo budget — because an empty result was
    never written back."""
    sess, pc = _Sess(), {"version": cache.VERSION, "entries": {}}
    listing = {"source": "morizon", "url": "https://m/1"}
    for day in range(1, 6):
        photomatch.attach_hashes([dict(listing)], session=sess, cache=pc,
                                 today=f"2026-08-0{day}", log=lambda *a: None,
                                 max_workers=1)
    # tried MISS_RETRIES times, then believed
    assert sess.calls == cache.MISS_RETRIES
    assert cache.get(pc, "https://m/1", "2026-08-05") == []
    # ...and re-probed once the verdict ages out
    assert cache.get(pc, "https://m/1", "2026-09-01") is None


def test_budget_skips_are_not_recorded_as_photo_misses():
    """An ad we never tried must not teach the cache it has no photos, or a few
    budget-starved runs would blind the pipeline to half the region."""
    sess, pc = _Sess(), {"version": cache.VERSION, "entries": {}}
    photomatch.attach_hashes([{"source": "morizon", "url": "https://m/2"}],
                             session=sess, cache=pc, today="2026-08-01",
                             log=lambda *a: None, budget_s=-1, max_workers=1)
    assert sess.calls == 0                       # budget was already blown
    assert pc["entries"] == {}                   # and nothing was learned


def test_photo_queue_puts_current_collisions_and_untried_work_first():
    cached = {"source": "gratka", "type": "flat", "area": 50, "rooms": 2,
              "price": 500000, "locality": "Kraków", "url": "cached"}
    same_size = {"source": "otodom", "type": "flat", "area": 50, "rooms": 2,
                 "price": 510000, "locality": "Tarnów", "url": "same-size"}
    cross_size = {"source": "nieruchomosci-online", "type": "flat",
                  "area": 51, "rooms": 2, "price": 500000,
                  "locality": "Kraków", "url": "cross-size"}
    old_history = {"source": "otodom", "type": "house", "area": 111,
                   "price": 700000, "locality": "Bochnia", "url": "old"}
    fresh_history = {"source": "gratka", "type": "house", "area": 222,
                     "price": 900000, "locality": "Olkusz", "url": "fresh"}
    retried_history = {"source": "otodom", "type": "house", "area": 333,
                       "price": 1100000, "locality": "Nowy Sącz", "url": "retry"}
    archived = {"source": "nieruchomosci-online", "type": "flat", "area": 44,
                "price": 400000, "locality": "Kraków", "url": "archived",
                "archived": True}
    pc = {"version": cache.VERSION,
          "entries": {
              "cached": {"h": [cache.pack(7)], "seen": "2026-08-01"},
              "retry": {"h": [], "seen": "2026-08-02", "tried": "2026-08-02",
                        "miss": 1},
          },
          "backlog": {"old": "2026-08-01"}}

    ordered, critical = photomatch.prioritize(
        [retried_history, fresh_history, archived, same_size, old_history,
         cross_size, cached],
        cache=pc, today="2026-08-03")

    # Exact-size and same-town/same-price collisions both affect today's
    # normalization. The positive cache hit is free and leads that queue.
    assert critical == {"cached", "same-size", "cross-size"}
    assert [row["url"] for row in ordered[:3]] == [
        "cached", "cross-size", "same-size",
    ]
    # In the history queue, old deferred work beats fresh work, while a prior
    # empty response is retried only after never-attempted listings.
    history_order = [row["url"] for row in ordered[3:]]
    assert history_order[0] == "old"
    assert history_order[-1] == "retry"
    assert history_order.index("fresh") < history_order.index("retry")


def test_legacy_gallery_miss_is_not_sorted_as_a_free_cover_hit():
    positive = {
        "source": "otodom", "type": "flat", "area": 50, "rooms": 2,
        "url": "positive", "image": "positive.jpg",
    }
    gallery_miss = {
        "source": "gratka", "type": "flat", "area": 50, "rooms": 2,
        "url": "gallery-miss", "image": "cover-never-tried.jpg",
    }
    pc = {"version": cache.VERSION, "entries": {}}
    cache.put(pc, "positive", [7], "2026-08-28")
    for _ in range(cache.MISS_RETRIES):
        cache.put(pc, "gallery-miss", [], "2026-08-28")

    ordered, critical = photomatch.prioritize(
        [gallery_miss, positive], cache=pc, today="2026-08-29")

    assert critical == {"positive", "gallery-miss"}
    assert [listing["url"] for listing in ordered] == [
        "positive", "gallery-miss",
    ]


def test_photo_metrics_separate_critical_and_history_deferrals(monkeypatch):
    ticks = iter([0, 0, 2, 2])
    monkeypatch.setattr(photomatch.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(photomatch, "listing_hashes",
                        lambda listing, session: ([7], [listing["url"] + ".jpg"]))
    listings = [
        {"source": "gratka", "url": "critical"},
        {"source": "gratka", "url": "history-1"},
        {"source": "gratka", "url": "history-2"},
    ]
    stats = photomatch.attach_hashes(
        listings, session=object(), log=lambda *a: None, max_workers=1,
        budget_s=1, critical_urls={"critical"})
    assert listings[0]["phashes"] == [7]
    assert listings[1]["phashes"] == listings[2]["phashes"] == []
    assert stats == {
        "listings": 3,
        "critical": 1,
        "history_only": 2,
        "cache_hits": 0,
        "cover_cache_hits": 0,
        "gallery_cache_hits": 0,
        "fetched": 1,
        "cover_fetched": 0,
        "gallery_fetched": 1,
        "with_photos": 1,
        "identified": 0,
        "deferred": 2,
        "critical_deferred": 0,
        "critical_with_photos": 1,
        "critical_without_photos": 0,
        "unresolved_size_groups": 0,
        "unresolved_size_listings": 0,
        "history_deferred": 2,
        "deferred_urls": ["history-1", "history-2"],
    }


def test_critical_ads_hash_card_covers_while_history_keeps_galleries(monkeypatch):
    calls = []

    def cover(listing, session):
        calls.append(("cover", listing["url"], session))
        return [11], [listing["image"]]

    def gallery(listing, session):
        calls.append(("gallery", listing["url"], session))
        return [22], [listing["url"] + ".gallery.jpg"]

    monkeypatch.setattr(photomatch, "cover_hashes", cover)
    monkeypatch.setattr(photomatch, "listing_hashes", gallery)
    session = object()
    pc = {"version": cache.VERSION, "entries": {}}
    listings = [
        {"source": "otodom", "url": "critical", "image": "card.jpg"},
        {"source": "otodom", "url": "history", "image": "other.jpg"},
    ]

    stats = photomatch.attach_hashes(
        listings, session=session, cache=pc, today="2026-08-28",
        critical_urls={"critical"}, log=lambda *a: None, max_workers=1,
    )

    assert calls == [
        ("cover", "critical", session),
        ("gallery", "history", session),
    ]
    assert listings[0]["phashes"] == [11]
    assert listings[1]["phashes"] == [22]
    assert cache.get_scope(pc, "critical") == "cover"
    assert cache.get_scope(pc, "history") == "gallery"
    assert stats["cover_fetched"] == 1
    assert stats["gallery_fetched"] == 1
    assert stats["critical_with_photos"] == 1
    assert stats["critical_without_photos"] == 0


def test_cover_hashes_fetches_only_the_card_image(monkeypatch):
    class Response:
        content = b"card bytes"

        def raise_for_status(self):
            pass

    class Session:
        def __init__(self):
            self.urls = []

        def get(self, url, **kwargs):
            self.urls.append(url)
            return Response()

    session = Session()
    monkeypatch.setattr(photomatch, "dhash", lambda content: 123)

    assert photomatch.cover_hashes(
        {"image": "https://img.test/card.jpg"}, session
    ) == ([123], ["https://img.test/card.jpg"])
    assert session.urls == ["https://img.test/card.jpg"]


def test_photo_fetching_defaults_to_the_no_retry_session(monkeypatch):
    session = object()
    seen = []
    monkeypatch.setattr(net, "probe_session", lambda: session)
    monkeypatch.setattr(
        photomatch, "listing_hashes",
        lambda listing, actual: (seen.append(actual) or ([], [])),
    )

    photomatch.attach_hashes(
        [{"source": "gratka", "url": "history"}],
        log=lambda *a: None, max_workers=1,
    )

    assert seen == [session]


def test_legacy_gallery_miss_cannot_suppress_a_critical_cover(monkeypatch):
    listing = {
        "source": "otodom", "url": "u", "image": "card.jpg",
        "type": "flat", "area": 50, "rooms": 2,
    }
    pc = {"version": cache.VERSION, "entries": {}}
    for _ in range(cache.MISS_RETRIES):
        cache.put(pc, "u", [], "2026-08-28")
    cover_calls = []
    monkeypatch.setattr(
        photomatch, "cover_hashes",
        lambda row, session: (cover_calls.append(row["url"])
                              or ([77], [row["image"]])),
    )

    stats = photomatch.attach_hashes(
        [listing], session=object(), cache=pc, today="2026-08-29",
        critical_urls={"u"}, log=lambda *a: None, max_workers=1,
    )

    assert cover_calls == ["u"]
    assert listing["phashes"] == [77]
    assert cache.get_scope(pc, "u") == "cover"
    assert stats["cover_fetched"] == 1
    assert stats["critical_without_photos"] == 0


def test_believed_cover_miss_still_gets_its_one_week_rest(monkeypatch):
    listing = {
        "source": "otodom", "url": "u", "image": "card.jpg",
        "type": "flat", "area": 50, "rooms": 2,
    }
    pc = {"version": cache.VERSION, "entries": {}}
    for _ in range(cache.MISS_RETRIES):
        cache.put(pc, "u", [], "2026-08-28", scope="cover")
    cover_calls = []
    monkeypatch.setattr(
        photomatch, "cover_hashes",
        lambda row, session: (cover_calls.append(row["url"]) or ([77], [])),
    )

    stats = photomatch.attach_hashes(
        [listing], session=object(), cache=pc, today="2026-08-29",
        critical_urls={"u"}, log=lambda *a: None, max_workers=1,
    )

    assert cover_calls == []
    assert stats["cover_cache_hits"] == 1
    assert stats["critical_without_photos"] == 1


def test_unresolved_size_groups_are_counted_for_the_conservative_gate(
        monkeypatch):
    listings = [
        {"source": source, "url": source, "type": "flat", "area": 50,
         "rooms": 2}
        for source in ("otodom", "gratka")
    ]
    monkeypatch.setattr(photomatch, "listing_hashes",
                        lambda listing, session: ([], []))

    stats = photomatch.attach_hashes(
        listings, session=object(), critical_urls={"otodom", "gratka"},
        log=lambda *a: None, max_workers=1,
    )

    assert stats["critical_without_photos"] == 2
    assert stats["unresolved_size_groups"] == 1
    assert stats["unresolved_size_listings"] == 2


# ---- the merge key, end to end ---------------------------------------------

def _mz(**kw):
    base = dict(source="morizon", source_id="2047889133", type="house",
                url="https://www.morizon.pl/oferta/x-mzn2047889133",
                area=130.0, rooms=4, price=799000, locality="Bieruń")
    base.update(kw)
    return base


def _gr(**kw):
    base = dict(source="gratka", source_id="48557359", type="house",
                url="https://gratka.pl/nieruchomosci/dom-bierun/oi/48557359",
                area=130.0, rooms=4, price=799000, locality="Bieruń")
    base.update(kw)
    return base


def test_twins_merge_with_no_photos_at_all():
    props = normalize.dedupe([_mz(gratka_id="48557359"), _gr()])
    assert len(props) == 1
    assert props[0]["sources"] == ["gratka", "morizon"]


def test_twins_merge_even_when_the_areas_disagree():
    """Usable vs total m2 splits the size groups; the portal id doesn't care."""
    props = normalize.dedupe([_mz(gratka_id="48557359", area=118.0), _gr(area=130.0)])
    assert len(props) == 1 and props[0]["area"] == 130.0


def test_twins_merge_when_neither_states_an_area():
    props = normalize.dedupe([_mz(gratka_id="48557359", area=None), _gr(area=None)])
    assert len(props) == 1 and props[0]["sources"] == ["gratka", "morizon"]


def test_an_unmatched_gratka_id_changes_nothing():
    props = normalize.dedupe([_mz(gratka_id="99999999", area=61.0), _gr(area=88.0)])
    assert len(props) == 2
    props = normalize.dedupe([_mz(gratka_id=None, area=61.0), _gr(area=88.0)])
    assert len(props) == 2


def test_a_twin_never_swallows_a_different_property_type():
    props = normalize.dedupe([_mz(gratka_id="48557359", type="flat", area=61.0),
                              _gr(type="house", area=61.0)])
    assert len(props) == 2


def test_twins_keep_merging_with_the_other_portals():
    """gratka merges with otodom on size+photos; pairing it with morizon must
    not pull it out of that group."""
    oto = dict(source="otodom", source_id="1", type="house", area=130.0, rooms=4,
               url="https://otodom.pl/a", price=805000, locality="Bieruń",
               phashes=[1 << 8])
    props = normalize.dedupe([_mz(gratka_id="48557359", phashes=[1 << 8]),
                              _gr(phashes=[1 << 8]), oto])
    assert len(props) == 1
    assert props[0]["sources"] == ["otodom", "gratka", "morizon"]


def test_a_twin_costs_no_photo_fetch():
    """A morizon ad carrying gratka's ad id is already identified; hashing it
    answers a question nobody is asking. ~8 700 fetches a run, out of a phase
    that starved 9 177-18 296 listings of a budget it cannot stretch."""
    raw = [_mz(gratka_id="48557359"), _gr()]
    assert normalize.link_twins(raw) == 1
    sess, said = _Sess(), []
    photomatch.attach_hashes(raw, session=sess, log=said.append, max_workers=1)
    assert sess.calls == 1, "the identified half was still fetched"
    assert "identified by their twin" in said[0]


def test_a_skipped_twin_is_not_recorded_as_a_photo_miss():
    """Same rule as a budget skip: an ad we deliberately never fetched must not
    teach the cache it has no photos."""
    raw = [_mz(gratka_id="48557359"), _gr()]
    normalize.link_twins(raw)
    pc = {"version": cache.VERSION, "entries": {}}
    photomatch.attach_hashes(raw, session=_Sess(), cache=pc, today="2026-08-01",
                             log=lambda *a: None, max_workers=1)
    assert raw[0]["url"] not in pc["entries"]


def test_linking_twins_early_leaves_the_merge_exactly_as_it_was():
    """`dedupe` calls `link_twins` again — the linking must also hold when
    hashing is off entirely — so running it early has to be idempotent."""
    raw = [_mz(gratka_id="48557359"), _gr()]
    normalize.link_twins(raw)
    props = normalize.dedupe(raw)
    assert len(props) == 1 and props[0]["sources"] == ["gratka", "morizon"]


def test_a_twins_photos_come_from_the_half_that_was_fetched():
    """Skipping the morizon half must not cost the property its photos, or the
    pair stops merging with otodom and n-online."""
    raw = [_mz(gratka_id="48557359"), _gr()]
    pc = {"version": cache.VERSION, "entries": {}}
    cache.put(pc, raw[1]["url"], [7], "2026-08-01", image_urls=["g1.jpg"])
    normalize.link_twins(raw)
    photomatch.attach_hashes(raw, session=_Sess(), cache=pc, today="2026-08-01",
                             log=lambda *a: None, max_workers=1)
    assert raw[0]["phashes"] == [] and raw[1]["phashes"] == [7]
    props = normalize.dedupe(raw)
    assert props[0]["phashes"] == [7] and props[0]["photo_urls"] == ["g1.jpg"]


def test_internal_link_field_never_reaches_the_payload():
    props = normalize.dedupe([_mz(gratka_id="48557359"), _gr()])
    assert "_twin" not in props[0] and "gratka_id" not in props[0]
    assert all("_twin" not in o for o in props[0]["offers"])
