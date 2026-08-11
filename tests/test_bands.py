"""Price-band subdivision — the general answer to "the portal won't show us".

Every portal serves far less than it holds (otodom 18 505 flats behind a
~7 200-ad window, gratka/morizon 9 856 behind a 7 000-ad 404 wall, olx 5 503
behind 1 000), and their location taxonomies will never agree. Price is the one
axis all four filter on, verified live per portal.

Offline: the scrapers' page loops are driven by a fake session that honours the
price parameters, so "did the band actually narrow the search" is a real
assertion and not a mock returning whatever it was told to.
"""
from scraper import bands, coverage, gratka, morizon


def test_seed_bands_partition_the_whole_price_line():
    bs = bands.seed_bands()
    assert bs[0][0] == 0 and bs[-1][1] is None
    for (_, hi), (lo, _) in zip(bs, bs[1:]):
        assert hi == lo, "bands must touch, with no gap and no overlap"


def test_bands_are_half_open_so_a_boundary_price_lands_in_one_band():
    lo = bands.params("otodom", 300_000, 400_000)
    hi = bands.params("otodom", 400_000, 500_000)
    assert lo["priceMax"] == "399999" and hi["priceMin"] == "400000"
    # an open-ended band states only the bound it has
    assert bands.params("gratka", 0, 200_000) == {"cena-calkowita:max": "199999"}
    assert bands.params("gratka", 3_000_000, None) == {"cena-calkowita:min": "3000000"}


def test_every_portals_parameters_are_the_probed_ones():
    """Verified against the live portals; gratka/morizon re-probed 2026-08-09."""
    assert bands.qs("otodom", 300_000, 400_000) == "priceMin=300000&priceMax=399999"
    assert bands.qs("gratka", 200_000, 300_000) == \
        "cena-calkowita:min=200000&cena-calkowita:max=299999"
    assert bands.qs("morizon", 200_000, 300_000) == \
        "ps[price_from]=200000&ps[price_to]=299999"
    assert bands.qs("olx", 0, 200_000) == "search[filter_float_price:to]=199999"
    assert bands.qs("nieruchomosci-online", 0, 100) == ""   # no band support


def test_bisect_always_terminates():
    lo, hi = 0, 20_000
    depth = 0
    while (halves := bands.bisect(lo, hi)) and depth < 50:
        lo, hi = halves[0]
        depth += 1
    assert depth < 50, "bisection must bottom out, not loop"
    assert bands.bisect(0, bands.MIN_BAND) is None
    # an open top still narrows
    a, b = bands.bisect(3_000_000, None)
    assert a == (3_000_000, 6_000_000) and b == (6_000_000, None)
    assert bands.bisect(0, None)[0] == (0, 1_000_000)


def test_overflows_reads_the_stated_total_and_the_stop_reason():
    over = coverage.row("otodom", "flat", None, 200, 7000, coverage.OK,
                        portal_total=18505)
    assert bands.overflows(over, "otodom") is True
    fine = coverage.row("otodom", "house", None, 30, 2000, coverage.OK,
                        portal_total=2000)
    assert bands.overflows(fine, "otodom") is False
    capped = coverage.row("olx", "flat", "x", 25, 900, coverage.PORTAL_CAP)
    assert bands.overflows(capped, "olx") is True


def test_a_failed_search_is_not_subdivided():
    """A request that failed will fail the same way with a price filter on it —
    treating an error as overflow makes one broken search recurse into dozens."""
    err = coverage.row("olx", "flat", "x", 1, 0, coverage.ERROR)
    assert bands.overflows(err, "olx") is False


def test_check_totals_flags_ads_that_match_no_band():
    said = []
    seeds = [coverage.row("gratka", "flat", "a", 1, 1, coverage.OK, portal_total=4000),
             coverage.row("gratka", "flat", "b", 1, 1, coverage.OK, portal_total=4000)]
    assert bands.check_totals("gratka", "flat", 9856, seeds, log=said.append) is False
    assert "1856 ads match no band" in said[0]
    assert bands.check_totals("gratka", "flat", 8000, seeds, log=said.append) is True


# ---- driven through a real scraper page loop --------------------------------

META = '<meta content="Mieszkania na sprzedaż. {n} ogłoszeń." name="description">'


CEILING = 1_000_000
# Small on purpose: the shape (wall < stock, bands narrower than the wall) is
# what is under test, and a full-size portal makes this file take half a minute.
STOCK, WALL = 1000, 20


class BandedSession:
    """A portal holding `stock` ads priced evenly across 0..1M, serving 35 a
    page and refusing to paginate past `wall` — i.e. gratka and morizon.

    One global set of ads, addressed by price, so a band returns *the same ads*
    the unbanded search would have returned in that price range. Without that
    the bands would invent fresh listings and "subdivision found more" would be
    an artifact of the fake rather than a property of the code.
    """

    def __init__(self, stock=9856, wall=200, per_page=35):
        self.stock, self.wall, self.per_page = stock, wall, per_page
        self.urls = []

    def price_of(self, i):
        return i * CEILING // self.stock

    def _band(self, url):
        lo, hi = 0, CEILING
        for part in url.split("?")[-1].split("&"):
            if ":min=" in part or "price_from]=" in part:
                lo = int(part.split("=")[1])
            elif ":max=" in part or "price_to]=" in part:
                hi = int(part.split("=")[1]) + 1
        return lo, hi

    def get(self, url, **kw):
        self.urls.append(url)
        page = int(url.split("page=")[1].split("&")[0]) if "page=" in url else 1
        lo, hi = self._band(url)
        matching = [i for i in range(self.stock) if lo <= self.price_of(i) < hi]
        if page > self.wall:
            return _Resp([], 404)
        start = (page - 1) * self.per_page
        ids = [f"ad-{i}" for i in matching[start:start + self.per_page]]
        return _Resp(ids, 200, META.format(n=len(matching)))


class _RefusingSession:
    """A portal that refuses the first `refusals` requests outright — otodom's
    405, OLX's page-1 block — and then serves normally."""

    def __init__(self, inner, refusals):
        self.inner, self.refusals = inner, refusals

    def get(self, url, **kw):
        if self.refusals > 0:
            self.refusals -= 1
            raise IOError("405 Client Error: Not Allowed")
        return self.inner.get(url, **kw)


class _Resp:
    def __init__(self, ids, status, head=""):
        self.status_code = status
        self.text = head + "".join(
            f'<div data-cy="card"><a data-cy="propertyUrl" href="/x/{i}"></a>'
            f'<span data-cy="cardPropertyOfferPrice">500 000 zł</span></div>'
            for i in ids)

    def raise_for_status(self):
        pass


def test_gratka_bands_recover_everything_the_wall_hid():
    s = BandedSession(stock=STOCK, wall=WALL)
    out = gratka.scrape(max_pages=500, delay=0, session=s, log=lambda *a: None,
                        types=("flat",))
    cov = gratka.scrape.last_coverage
    reachable = WALL * s.per_page
    assert cov[0]["stopped"] == coverage.PORTAL_CAP    # the unbanded pass, walled
    assert cov[0]["listings"] == reachable
    # the whole stated total, not just the reachable window, and no ad twice
    assert len(out) == len({l["url"] for l in out}) == STOCK
    assert len(out) > reachable
    assert any("cena-calkowita:min=" in u for u in s.urls)


def test_morizon_bands_too_and_the_unbanded_pass_is_kept():
    s = BandedSession(stock=STOCK, wall=WALL)
    out = morizon.scrape(max_pages=500, delay=0, session=s, log=lambda *a: None,
                         types=("flat",))
    assert len(out) == len({l["url"] for l in out}) == STOCK
    assert any("ps[price_from]=" in u for u in s.urls)
    # additive: the unbanded pass ran first and kept every ad it found
    assert morizon.scrape.last_coverage[0]["listings"] == WALL * s.per_page


def test_a_band_whose_first_page_is_all_duplicates_keeps_going():
    """A band re-sorts the results, so its early pages are usually ads the
    unbanded pass already took. Stopping on "nothing new here" would abandon
    the band at page 1 and quietly lose everything behind it."""
    s = BandedSession(stock=STOCK, wall=WALL)
    gratka.scrape(max_pages=500, delay=0, session=s, log=lambda *a: None,
                  types=("flat",))
    cheap = [r for r in gratka.scrape.last_coverage
             if (r.get("tag") or "").endswith("0-200k")]
    assert cheap and cheap[0]["pages"] > 1
    assert cheap[0]["listings"] == 0, "this band is entirely already-seen ads"


def test_a_portal_within_its_window_is_never_banded():
    """Subdivision must cost nothing when it isn't needed."""
    s = BandedSession(stock=STOCK, wall=200)
    gratka.scrape(max_pages=500, delay=0, session=s, log=lambda *a: None,
                  types=("flat",))
    assert len(gratka.scrape.last_coverage) == 1
    assert not any("cena-calkowita" in u for u in s.urls)


def test_banded_off_restores_the_old_behaviour():
    s = BandedSession(stock=STOCK, wall=WALL)
    gratka.scrape(max_pages=500, delay=0, session=s, log=lambda *a: None,
                  types=("flat",), banded=False)
    assert len(gratka.scrape.last_coverage) == 1
    assert not any("cena-calkowita" in u for u in s.urls)


def test_a_bands_stated_total_is_judged_on_what_the_portal_served():
    """gratka/morizon never passed `served`, so `coverage.seen_by` fell back to
    the NEW count and every band read as truncated: run 31367424054 logged
    'gratka flat/slaskie/0-200k: collected 82 of 536 (15.3%) — subdivide it'
    for a band that had walked all 16 of its pages and seen every one of them.
    Twenty such lines per run, in a log whose warnings are the whole point."""
    for portal in (gratka, morizon):
        s = BandedSession(stock=STOCK, wall=WALL)
        portal.scrape(max_pages=500, delay=0, session=s, log=lambda *a: None,
                      types=("flat",))
        cheap = [r for r in portal.scrape.last_coverage
                 if (r.get("tag") or "").endswith("0-200k")][0]
        assert cheap["listings"] == 0        # every ad already held
        assert cheap["served"] == cheap["portal_total"]   # ...but all of them seen
        assert coverage.warnings([cheap]) == []
        # and the source's pct now measures coverage rather than novelty
        rows = portal.scrape.last_coverage
        src = coverage.summarise(rows)["by_source"][rows[0]["source"]]
        novelty = coverage.covered(src["listings"], src["portal_total"])
        assert src["seen"] > src["listings"] and src["pct"] > novelty


# ---- waiting a portal out ----------------------------------------------------

def _walker(script, calls):
    """A `walk` for subdivide: `script` maps a band tag to the rows it returns
    in order, so a band can fail once and succeed on the retry."""
    def walk(lo, hi, tag):
        calls.append(tag)
        queued = script.get(tag)
        if queued:
            return queued.pop(0)
        return coverage.row("otodom", "flat", tag, 1, 10, coverage.OK,
                            portal_total=10)
    return walk


def test_searches_are_paced_apart_not_only_pages():
    """`time.sleep(delay)` in the page loops paces pages within one search;
    nothing paced one search against the next, so a subdivision fired its
    whole band queue at the portal back to back."""
    slept, calls = [], []
    bands.subdivide("otodom", _walker({}, calls), log=lambda *a: None,
                    delay=0.7, sleep=slept.append)
    assert len(calls) == len(bands.seed_bands())
    assert slept == [0.7 * bands.SEARCH_PAUSE] * len(calls)
    assert 0.7 * bands.SEARCH_PAUSE > 0.7, "a search needs a wider gap than a page"


def test_a_refused_band_is_walked_again_after_a_cooldown():
    """Otodom 405'd band `300k-400k` at page 5 and refused the seven bands
    after it on page 1, then served the eighth (runs 31408840562/31422141701):
    the refusal is transient and nothing in the stack waited it out."""
    refused = coverage.row("otodom", "flat", "300k-400k", 5, 300, coverage.ERROR,
                           portal_total=3348)
    recovered = coverage.row("otodom", "flat", "300k-400k", 47, 3300,
                             coverage.OK, portal_total=3348)
    calls, slept, said = [], [], []
    rows, _ = bands.subdivide(
        "otodom", _walker({"300k-400k": [refused, recovered]}, calls),
        log=said.append, delay=0.7, sleep=slept.append)
    assert calls.count("300k-400k") == 2                    # asked once more
    assert 0.7 * bands.ERROR_COOLDOWN in slept              # ...after a wait
    assert any("refused" in m for m in said)
    band = [r for r in rows if r["tag"] == "300k-400k"]
    assert len(band) == 1 and band[0]["listings"] == 3300, \
        "the retry replaces the failed row — a recovered band is not two rows"


def test_a_band_refused_twice_is_left_alone():
    """One retry, never a loop: a portal that is still refusing after the
    cooldown must cost one extra request, not a queue that never drains."""
    refused = lambda: coverage.row("otodom", "flat", "0-200k", 1, 0, coverage.ERROR)
    calls = []
    rows, seeds = bands.subdivide(
        "otodom", _walker({"0-200k": [refused(), refused()]}, calls),
        log=lambda *a: None, delay=0, sleep=lambda _: None)
    assert calls.count("0-200k") == 2
    assert [r for r in rows if r["tag"] == "0-200k"][0]["stopped"] == coverage.ERROR
    # and an errored band is still not treated as overflow, so it is not bisected
    assert len(rows) == len(bands.seed_bands())


def test_a_refused_first_search_does_not_lose_the_whole_portal():
    """`overflows` will not subdivide an error row — rightly, a filtered search
    fails the same way — so a refusal on page 1 of the UNBANDED search leaves
    nothing to fall back on and the portal contributes zero. That is exactly
    what OLX did on both types in run 31422141701."""
    s = _RefusingSession(BandedSession(stock=STOCK, wall=WALL), refusals=1)
    out = gratka.scrape(max_pages=500, delay=0, session=s, log=lambda *a: None,
                        types=("flat",))
    rows = gratka.scrape.last_coverage
    assert rows[0]["stopped"] != coverage.ERROR, "the retry served the search"
    assert len(out) == STOCK, "and the bands behind it ran, as on a clean run"


def test_the_wait_is_budgeted_per_portal_not_per_search():
    """A portal refusing everything refuses the retries too. OLX walks ~120
    towns; one 28 s cooldown each would be an hour of sleeping against a
    350-min cap with no headroom."""
    refused = lambda: coverage.row("olx", "flat", "x", 1, 0, coverage.ERROR)
    calls, slept, said = [], [], []

    def walk():
        calls.append(1)
        return refused()

    pacer = bands.Pacer("olx", delay=0.7, log=said.append, sleep=slept.append,
                        max_cooldowns=2)
    for i in range(4):
        pacer.attempt(f"town{i}", walk)
    assert len(calls) == 6, "two searches asked twice, the other two once"
    assert slept.count(0.7 * bands.ERROR_COOLDOWN) == 2
    assert any("no retry budget left" in m for m in said)
    # and the shipped budget is minutes, not hours
    assert bands.MAX_COOLDOWNS * bands.ERROR_COOLDOWN * 0.7 < 10 * 60


def test_one_budget_covers_a_portals_bands_and_its_own_searches():
    """The unbanded search, the towns and the bands share one pacer, so the
    budget is spent across a portal's whole run rather than per subdivision."""
    refused = lambda *a: coverage.row("otodom", "flat", "x", 1, 0, coverage.ERROR)
    calls, said = [], []
    pacer = bands.Pacer("otodom", delay=0, log=said.append, sleep=lambda _: None,
                        max_cooldowns=1)
    pacer.attempt("flat", lambda: (calls.append("unbanded"), refused())[1])
    bands.subdivide("otodom", lambda lo, hi, tag: (calls.append(tag), refused())[1],
                    log=said.append, pacer=pacer)
    assert calls.count("unbanded") == 2, "the first search spent the budget"
    assert calls.count("0-200k") == 1, "so the first band got no retry"


def test_a_healthy_subdivision_never_waits_out_an_error():
    """Pacing is per search; the cooldown must cost nothing when nothing failed."""
    slept = []
    bands.subdivide("gratka", _walker({}, []), log=lambda *a: None,
                    delay=0.5, sleep=slept.append)
    assert set(slept) == {0.5 * bands.SEARCH_PAUSE}
