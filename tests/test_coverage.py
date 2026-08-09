"""Overflow detection: did a search finish, or did something cut it short?

The bug this guards against is silent truncation — a capped search returns a
plausible pile of listings and nothing says more exist. With the old 50-page
default every paginated portal was stopping on our cap inside śląskie alone.
Offline: the scrapers' page loops are driven by a fake session.

The second half of the file guards the harder version of the same bug, found
2026-08-08: a search that stops for an innocent reason and is truncated anyway
(gratka 404s past page 200 exactly like it 404s past its last page; OLX states
its cap as a smaller `totalElements` and a matching `totalPages`). Only the
portal's own stated total tells those apart.
"""
import json

from scraper import coverage, gratka, morizon, olx
from scraper.normalize import stated_total


def test_stop_reason():
    # ran out of results -> fine, however few pages that took
    assert coverage.stop_reason(3, 200, total_pages=3) == coverage.OK
    assert coverage.stop_reason(1, 200, hit_end=True) == coverage.OK
    # walked to our cap while the portal still had pages -> we truncated it
    assert coverage.stop_reason(200, 200, total_pages=812) == coverage.OUR_CAP
    assert coverage.stop_reason(50, 50) == coverage.OUR_CAP


def test_summarise_and_warnings():
    rows = [
        coverage.row("gratka", "house", "slaskie", 72, 2509, coverage.OK),
        coverage.row("gratka", "flat", "slaskie", 200, 7000, coverage.OUR_CAP,
                     portal_pages=812),
        coverage.row("olx", "house", "slaskie", 25, 900, coverage.PORTAL_CAP,
                     portal_pages=140),
    ]
    s = coverage.summarise(rows)
    assert s["by_source"]["gratka"] == {"searches": 2, "pages": 272,
                                        "listings": 9509, "truncated": 1}
    assert [r["source"] for r in s["truncated"]] == ["gratka", "olx"]
    w = coverage.warnings(rows)
    assert len(w) == 2
    assert "812" in w[0] and "RENTGEN_MAX_PAGES" in w[0]
    assert "subdivision" in w[1]
    # a clean run says nothing at all
    assert coverage.warnings([rows[0]]) == []


# --- the portal's own count is the ground truth ------------------------------

# verbatim from the live meta descriptions, 2026-08-08
GRATKA_META = ('<meta content="Mieszkania na sprzedaż śląskie. 9856 ogłoszeń. '
               'Sprawdź!" name="description">')
MORIZON_META = ('<meta content="Mieszkania na sprzedaż - ponad 9000 ogłoszeń '
                '„sprzedam mieszkanie”" name="description">')


def test_stated_total_reads_both_frontends():
    assert stated_total(GRATKA_META) == (9856, False)
    # morizon says "ponad" and rounds to thousands -> a lower bound
    assert stated_total(MORIZON_META) == (9000, True)
    # thousands separators (the portals use a non-breaking space)
    assert stated_total("18 505 ogłoszeń")[0] == 18505
    # "Dodaj ogłoszenie" and friends carry no number and must not match
    assert stated_total("<span>Dodaj ogłoszenie</span>") == (None, False)
    assert stated_total("") == (None, False)


def test_short_of_total_needs_a_total():
    assert coverage.short_of_total(7000, 9856) is True
    assert coverage.short_of_total(2509, 2513) is False    # inside the slack
    # an unknown total is not evidence of completeness
    assert coverage.short_of_total(7000, None) is False
    assert coverage.covered(7000, 9856) == 71.0
    assert coverage.covered(7000, None) is None


def test_warns_when_a_clean_stop_falls_short_of_the_portals_count():
    """The gratka trap: page 201 404s because the portal stops at 200, not
    because the results ran out. Stop reason says "end"; the total says no."""
    row = coverage.row("gratka", "flat", "slaskie", 200, 7000, coverage.OK,
                       portal_total=9856)
    w = coverage.warnings([row])
    assert len(w) == 1 and "9856" in w[0] and "71.0%" in w[0]
    # a lower-bound total (morizon) proves truncation the same way...
    lo = coverage.row("morizon", "flat", "slaskie", 200, 7000, coverage.OK,
                      portal_total=9000, total_is_min=True)
    assert "≥9000" in coverage.warnings([lo])[0]
    # ...but collecting MORE than a rounded-down total proves nothing
    over = coverage.row("morizon", "house", "slaskie", 72, 2513, coverage.OK,
                        portal_total=2000, total_is_min=True)
    assert coverage.warnings([over]) == []


def test_summarise_carries_the_totals():
    rows = [
        coverage.row("gratka", "flat", "slaskie", 200, 7000, coverage.PORTAL_CAP,
                     portal_total=9856),
        coverage.row("gratka", "house", "slaskie", 72, 2509, coverage.OK,
                     portal_total=2513),
    ]
    s = coverage.summarise(rows)["by_source"]["gratka"]
    assert s["portal_total"] == 12369 and s["listings"] == 9509
    assert s["pct"] == 76.9
    assert "total_is_min" not in s


# --- gratka / morizon: the 200-page wall ------------------------------------

class FakeCardResp:
    def __init__(self, cards, total_html="", status=200):
        self.status_code = status
        self.text = total_html + "".join(
            f'<div data-cy="card"><a data-cy="propertyUrl" href="/x/{c}"></a>'
            f'<span data-cy="cardPropertyOfferPrice">500 000 zł</span></div>'
            for c in cards)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise AssertionError("should not be raised for 404 (handled)")


class WalledSession:
    """Serves `per_page` cards up to `wall`, then 404s — while the header keeps
    claiming `stated` ads. That is gratka/morizon: a 404 at page 201."""
    def __init__(self, wall, stated_html, per_page=35):
        self.wall, self.stated_html, self.per_page = wall, stated_html, per_page

    def get(self, url, **kw):
        page = int(url.rsplit("page=", 1)[1]) if "page=" in url else 1
        if page > self.wall:
            return FakeCardResp([], status=404)
        return FakeCardResp([f"{page}-{i}" for i in range(self.per_page)],
                            self.stated_html)


def test_gratka_404_wall_is_reported_as_a_portal_cap():
    gratka.scrape(max_pages=500, delay=0, log=lambda *a: None, types=("flat",),
                  banded=False,
                  session=WalledSession(wall=200, stated_html=GRATKA_META))
    row = gratka.scrape.last_coverage[0]
    assert row["pages"] == 200
    assert row["portal_total"] == 9856
    assert row["listings"] == 7000                 # 200 x 35
    assert row["stopped"] == coverage.PORTAL_CAP   # NOT "end" — 7000 < 9856


def test_gratka_real_end_stays_clean():
    """The same 404, but the portal's count agrees we got everything."""
    meta = '<meta content="Domy na sprzedaż. 350 ogłoszeń." name="description">'
    gratka.scrape(max_pages=500, delay=0, log=lambda *a: None, types=("flat",),
                  banded=False,
                  session=WalledSession(wall=10, stated_html=meta))
    row = gratka.scrape.last_coverage[0]
    assert row["listings"] == 350 and row["stopped"] == coverage.OK
    assert coverage.warnings([row]) == []


def test_morizon_lower_bound_total_still_catches_the_wall():
    morizon.scrape(max_pages=500, delay=0, log=lambda *a: None, types=("flat",),
                   banded=False,
                   session=WalledSession(wall=200, stated_html=MORIZON_META))
    row = morizon.scrape.last_coverage[0]
    assert row["portal_total"] == 9000 and row["total_is_min"] is True
    assert row["stopped"] == coverage.PORTAL_CAP


# --- OLX: the one portal with a cap of its own ------------------------------

def _ad(i):
    return {"id": i, "url": f"https://www.olx.pl/d/oferta/{i}", "title": f"ad {i}",
            "price": {"regularPrice": {"value": 500000 + i}}, "params": [],
            "location": {"cityName": "Gliwice"}, "photos": [], "user": {}}


class FakeResp:
    def __init__(self, ads, total_pages, visible=None, servable=None):
        listing = {"ads": ads, "totalPages": total_pages}
        if visible is not None:
            listing["visibleElements"] = visible
        if servable is not None:
            listing["totalElements"] = servable
        payload = json.dumps({"listing": {"listing": listing}})
        self.text = ('<script>window.__PRERENDERED_STATE__ = '
                     + json.dumps(payload) + ';</script>')

    def raise_for_status(self):
        pass


class FakeSession:
    """Serves `per_page` ads per page but refuses to paginate past `hard_cap`,
    while still claiming `total_pages` — exactly OLX's behaviour."""
    def __init__(self, total_pages, hard_cap=25, per_page=2,
                 visible=None, servable=None):
        self.total_pages, self.hard_cap, self.per_page = total_pages, hard_cap, per_page
        self.visible, self.servable = visible, servable
        self.urls = []

    def get(self, url, **kw):
        self.urls.append(url)
        page = int(url.rsplit("page=", 1)[1])
        base = abs(hash(url.split("?")[0])) % 1000
        if page > self.hard_cap:
            return FakeResp([], self.total_pages, self.visible, self.servable)
        ads = [_ad(base * 1000 + page * 10 + i) for i in range(self.per_page)]
        return FakeResp(ads, self.total_pages, self.visible, self.servable)


def test_olx_records_portal_cap_and_subdivides():
    s = FakeSession(total_pages=140)
    towns = {"gliwice": "Gliwice", "katowice": "Katowice"}
    out = olx.scrape(max_pages=200, delay=0, session=s, log=lambda *a: None,
                     types=("house",), towns=towns, banded=False)
    cov = olx.scrape.last_coverage
    region = cov[0]
    assert region["stopped"] == coverage.PORTAL_CAP   # 25 < 140 claimed pages
    assert region["pages"] == olx.HARD_PAGE_CAP
    assert region["portal_pages"] == 140
    # ...so it subdivided, one extra search per town
    assert [r.get("tag") for r in cov[1:]] == ["gliwice", "katowice"]
    assert any("/domy/sprzedaz/gliwice/" in u for u in s.urls)
    # subdivision is ADDITIVE: region ads kept, town ads merged in, no dupes
    assert len(out) == len({l["url"] for l in out})
    assert len(out) > region["listings"]


def test_olx_does_not_subdivide_a_complete_search():
    """No cap hit -> no extra requests. Subdivision costs nothing when unneeded."""
    s = FakeSession(total_pages=3)
    olx.scrape(max_pages=200, delay=0, session=s, log=lambda *a: None,
               types=("house",), towns={"gliwice": "Gliwice"})
    cov = olx.scrape.last_coverage
    assert len(cov) == 1 and cov[0]["stopped"] == coverage.OK
    assert all("slaskie" in u for u in s.urls)


def test_olx_without_towns_still_reports_the_cap():
    """Subdivision needs a town list; without one we must still say we were cut
    off rather than silently returning a partial region."""
    s = FakeSession(total_pages=140)
    olx.scrape(max_pages=200, delay=0, session=s, log=lambda *a: None,
               types=("house",), towns=None, banded=False)
    assert olx.scrape.last_coverage[0]["stopped"] == coverage.PORTAL_CAP


def test_olx_cap_stated_as_a_smaller_total_is_still_a_cap():
    """The live shape (measured 2026-08-08): OLX answers visibleElements 5503,
    totalElements 1000 and totalPages 25, then serves those 25 pages happily.
    Walking them looks like a finished search — it is the cap, stated instead
    of hit, and it is why śląskie yielded 470 listings with no warning."""
    s = FakeSession(total_pages=25, hard_cap=99, visible=5503, servable=1000)
    towns = {"gliwice": "Gliwice"}
    olx.scrape(max_pages=200, delay=0, session=s, log=lambda *a: None,
               types=("house",), towns=towns, banded=False)
    cov = olx.scrape.last_coverage
    assert cov[0]["pages"] == 25                      # walked all it was offered
    assert cov[0]["portal_total"] == 5503
    assert cov[0]["stopped"] == coverage.PORTAL_CAP   # was silently "end"
    assert [r.get("tag") for r in cov[1:]] == ["gliwice"]   # so it subdivides


def test_olx_complete_search_reports_its_total_without_warning():
    s = FakeSession(total_pages=3, hard_cap=99, visible=6, servable=6)
    olx.scrape(max_pages=200, delay=0, session=s, log=lambda *a: None,
               types=("house",), towns={"gliwice": "Gliwice"})
    row = olx.scrape.last_coverage[0]
    assert row["stopped"] == coverage.OK and row["portal_total"] == 6
    assert len(olx.scrape.last_coverage) == 1
    assert coverage.warnings([row]) == []


# --- served vs kept: our own filtering is not missed coverage ----------------

def test_pct_measures_what_the_portal_served_not_what_we_kept():
    """OLX states `visibleElements` for every ad matching a search, but we drop
    the ones it syndicates from Otodom (already collected at the source). On a
    town search that is most of them, so comparing kept-vs-stated declared all
    ~60 town searches truncated: the 2026-08-08 run printed 126 warnings, nearly
    all false, which is a very effective way to stop anyone reading them."""
    row = coverage.row("olx", "house", "katowice", 2, 3, coverage.OK,
                       portal_total=63, served=63)
    assert coverage.seen_by(row) == 63
    assert coverage.warnings([row]) == []          # saw everything, kept 3
    s = coverage.summarise([row])["by_source"]["olx"]
    assert s["listings"] == 3 and s["seen"] == 63 and s["pct"] == 100.0


def test_a_genuinely_truncated_search_still_warns_loudly():
    """The suppression must key on what was SERVED, not merely on `served`
    being present — otherwise it would hide the real thing."""
    row = coverage.row("olx", "house", "katowice", 25, 3, coverage.OK,
                       portal_total=1733, served=500)
    w = coverage.warnings([row])
    assert len(w) == 1 and "1733" in w[0] and "kept 3" in w[0]


def test_served_is_omitted_when_nothing_was_filtered():
    row = coverage.row("gratka", "flat", "slaskie", 10, 350, coverage.OK,
                       portal_total=350, served=350)
    assert "served" not in row
    assert "seen" not in coverage.summarise([row])["by_source"]["gratka"]
