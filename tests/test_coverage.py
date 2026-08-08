"""Overflow detection: did a search finish, or did something cut it short?

The bug this guards against is silent truncation — a capped search returns a
plausible pile of listings and nothing says more exist. With the old 50-page
default every paginated portal was stopping on our cap inside śląskie alone.
Offline: the scrapers' page loops are driven by a fake session.
"""
import json

from scraper import coverage, olx


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


# --- OLX: the one portal with a cap of its own ------------------------------

def _ad(i):
    return {"id": i, "url": f"https://www.olx.pl/d/oferta/{i}", "title": f"ad {i}",
            "price": {"regularPrice": {"value": 500000 + i}}, "params": [],
            "location": {"cityName": "Gliwice"}, "photos": [], "user": {}}


class FakeResp:
    def __init__(self, ads, total_pages):
        payload = json.dumps({"listing": {"listing": {
            "ads": ads, "totalPages": total_pages}}})
        self.text = ('<script>window.__PRERENDERED_STATE__ = '
                     + json.dumps(payload) + ';</script>')

    def raise_for_status(self):
        pass


class FakeSession:
    """Serves `per_page` ads per page but refuses to paginate past `hard_cap`,
    while still claiming `total_pages` — exactly OLX's behaviour."""
    def __init__(self, total_pages, hard_cap=25, per_page=2):
        self.total_pages, self.hard_cap, self.per_page = total_pages, hard_cap, per_page
        self.urls = []

    def get(self, url, **kw):
        self.urls.append(url)
        page = int(url.rsplit("page=", 1)[1])
        base = abs(hash(url.split("?")[0])) % 1000
        if page > self.hard_cap:
            return FakeResp([], self.total_pages)
        ads = [_ad(base * 1000 + page * 10 + i) for i in range(self.per_page)]
        return FakeResp(ads, self.total_pages)


def test_olx_records_portal_cap_and_subdivides():
    s = FakeSession(total_pages=140)
    towns = {"gliwice": "Gliwice", "katowice": "Katowice"}
    out = olx.scrape(max_pages=200, delay=0, session=s, log=lambda *a: None,
                     types=("house",), towns=towns)
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
               types=("house",), towns=None)
    assert olx.scrape.last_coverage[0]["stopped"] == coverage.PORTAL_CAP
